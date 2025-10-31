import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from django.utils import timezone

# Importar nuestros módulos de reportes
from .parser import parse_report_prompt
from .query_builder import build_report_query
from .generators import generate_excel_report, generate_pdf_report

logger = logging.getLogger(__name__)


class DynamicReportAPIView(APIView):
    """
    API View para generar reportes dinámicos basados en un prompt de texto.
    
    POST /api/reports/dynamic_report/
    Body: {
        "prompt": "reporte de ventas de la marca Samsung para octubre 2024 en pdf",
        "format": "pdf"  // Opcional: forzar formato (pdf, excel, json)
    }
    
    Permisos: Solo administradores
    
    Respuesta:
    - PDF/Excel: Archivo descargable
    - JSON: Lista de objetos con los datos del reporte
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        prompt_text = request.data.get('prompt')
        # Permitir que el frontend fuerce un formato (ej: desde un <select>)
        format_override = request.data.get('format', None)

        if not prompt_text:
            return Response(
                {"error": "Se requiere un 'prompt' en el cuerpo de la solicitud."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"Recibida solicitud de reporte: '{prompt_text}' (Formato override: {format_override})")

        # 1. Parsear el prompt
        options = parse_report_prompt(prompt_text)
        if format_override in ['pdf', 'excel', 'json']:
            options['format'] = format_override
        
        if options['errors']:
            return Response(
                {"error": f"Error al parsear el prompt: {options['errors']}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Construir la consulta
        try:
            queryset, headers = build_report_query(options)
        except Exception as e:
            logger.error(f"Error en Query Builder para prompt '{prompt_text}': {e}", exc_info=True)
            return Response(
                {"error": f"Error al construir la consulta: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if queryset is None:
            return Response(
                {"error": f"El módulo '{options.get('module')}' no está soportado o no se pudo generar la consulta."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not queryset.exists():
            logger.info(f"Reporte para '{prompt_text}' no arrojó resultados.")
            # Devolvemos 200 OK con mensaje, o un reporte vacío
            if options['format'] == 'json':
                return Response([], status=status.HTTP_200_OK)  # JSON vacío
            # Podríamos generar PDF/Excel vacíos si quisiéramos, pero un 200 con mensaje es más claro
            return Response(
                {"message": "La consulta no arrojó resultados."},
                status=status.HTTP_200_OK  # No es un error, solo no hay datos
            )

        # 3. Generar el archivo
        title = f"Reporte de {options['module'].capitalize()} ({timezone.now().strftime('%Y-%m-%d')})"
        
        try:
            if options['format'] == 'excel':
                logger.info("Generando reporte Excel...")
                return generate_excel_report(queryset, headers, title)
            
            elif options['format'] == 'pdf':
                logger.info("Generando reporte PDF...")
                return generate_pdf_report(queryset, headers, title, options['original_prompt'])
            
            else:  # 'json' (vista en pantalla)
                logger.info("Generando respuesta JSON...")
                # El queryset es un .values(), que es una lista de diccionarios, lista para JSON
                return Response(list(queryset), status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error al generar archivo para prompt '{prompt_text}': {e}", exc_info=True)
            return Response(
                {"error": f"Error al generar el archivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
