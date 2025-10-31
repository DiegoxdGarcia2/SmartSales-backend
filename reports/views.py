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
    API View para generar reportes dinámicos basados en un prompt de texto o opciones estructuradas.
    
    POST /api/reports/dynamic_report/
    
    Body (Opción 1 - Prompt de texto):
    {
        "prompt": "reporte de ventas de la marca Samsung para octubre 2024 en pdf",
        "format": "pdf"  // Opcional: forzar formato (pdf, excel, json)
    }
    
    Body (Opción 2 - Opciones estructuradas desde UI):
    {
        "options": {
            "module": "ventas",
            "format": "excel",
            "start_date": "2024-10-01T00:00:00Z",
            "end_date": "2024-10-31T23:59:59Z",
            "group_by": "category",
            "filters": {
                "brand_name": "Samsung"
            }
        }
    }
    
    Permisos: Solo administradores
    
    Respuesta:
    - PDF/Excel: Archivo descargable
    - JSON: Lista de objetos con los datos del reporte
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        prompt_text = request.data.get('prompt')
        # Obtener opciones estructuradas (para la nueva UI de selectores)
        options_structured = request.data.get('options', None)
        format_override = request.data.get('format', None)

        if not prompt_text and not options_structured:
            return Response(
                {"error": "Se requiere un 'prompt' o un objeto 'options'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        options = {}

        if options_structured and isinstance(options_structured, dict):
            # --- Ruta 1: Opciones Estructuradas (Nueva UI) ---
            logger.info(f"Recibida solicitud de reporte estructurado: {options_structured}")
            options = options_structured
            # Añadir prompt por defecto si no existe
            if 'original_prompt' not in options:
                options['original_prompt'] = 'Reporte estructurado'
            # El formato puede venir dentro de 'options' o como 'format_override'
            if format_override:
                options['format'] = format_override
            # Asegurar que 'errors' exista
            if 'errors' not in options:
                options['errors'] = []

        elif prompt_text:
            # --- Ruta 2: Prompt de Texto (Voz o Texto) ---
            logger.info(f"Recibida solicitud de reporte por prompt: '{prompt_text}' (Formato override: {format_override})")
            
            try:
                options = parse_report_prompt(prompt_text)
                if format_override in ['pdf', 'excel', 'json']:
                    options['format'] = format_override
            except Exception as e:
                logger.error(f"Error al parsear el prompt '{prompt_text}': {e}", exc_info=True)
                return Response(
                    {"error": f"Error al parsear el prompt: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            if options.get('errors'):
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
        title = f"Reporte de {options.get('module', 'General').capitalize()} ({timezone.now().strftime('%Y-%m-%d')})"
        
        try:
            if options.get('format') == 'excel':
                logger.info("Generando reporte Excel...")
                return generate_excel_report(queryset, headers, title)
            
            elif options.get('format') == 'pdf':
                logger.info("Generando reporte PDF...")
                return generate_pdf_report(queryset, headers, title, options.get('original_prompt', 'Reporte'))
            
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
