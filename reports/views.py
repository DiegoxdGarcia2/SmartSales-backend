import logging
import io
import csv
import openpyxl
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from django.http import HttpResponse
from django.utils import timezone
from dateutil.parser import parse as date_parse

# Importar nuestros módulos de reportes
from .parser import parse_report_prompt
from .query_builder import build_report_query
from .generators import generate_excel_report, generate_pdf_report, generate_csv_report

logger = logging.getLogger(__name__)


def generate_report_title(options: dict) -> str:
    """
    Genera un título descriptivo para el reporte basado en las opciones.
    
    Args:
        options: Diccionario con opciones del reporte
    
    Returns:
        str: Título descriptivo del reporte
    """
    module = options.get('module', 'General').capitalize()
    parts = [f"Reporte de {module}"]
    
    # Agregar filtros al título
    filters = options.get('filters', {})
    if filters.get('brand_name'):
        parts.append(f"Marca {filters['brand_name']}")
    if filters.get('category_name'):
        parts.append(f"Categoria {filters['category_name']}")
    if filters.get('user_username'):
        parts.append(f"Cliente {filters['user_username']}")
    
    # Agregar rango de fechas
    start_date = options.get('start_date')
    end_date = options.get('end_date')
    if start_date and end_date:
        # Formatear fechas
        start_str = start_date.strftime('%d-%m-%Y')
        end_str = end_date.strftime('%d-%m-%Y')
        
        # Si es el mismo día, mostrar solo una fecha
        if start_date.date() == end_date.date():
            parts.append(start_str)
        # Si es el mismo mes y año, mostrar rango simplificado
        elif start_date.month == end_date.month and start_date.year == end_date.year:
            parts.append(f"{start_date.strftime('%B %Y')}")
        else:
            parts.append(f"{start_str} a {end_str}")
    
    # Agregar agrupación
    group_by = options.get('group_by')
    if group_by:
        group_name = {
            'category': 'por Categoría',
            'brand': 'por Marca',
            'product': 'por Producto',
            'user': 'por Cliente',
            'mes': 'por Mes'
        }.get(group_by, f'por {group_by}')
        parts.append(group_name)
    
    return ' - '.join(parts)


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
            
            # 🔧 FIX: Parsear fechas si vienen como strings
            if 'start_date' in options and isinstance(options['start_date'], str):
                try:
                    parsed_date = date_parse(options['start_date'])
                    # Asegurar timezone-aware
                    if timezone.is_naive(parsed_date):
                        parsed_date = timezone.make_aware(parsed_date)
                    options['start_date'] = parsed_date.replace(hour=0, minute=0, second=0)
                    logger.debug(f"Fecha inicio parseada: {options['start_date']}")
                except Exception as e:
                    logger.error(f"Error parseando start_date '{options['start_date']}': {e}")
                    return Response(
                        {"error": f"Formato de start_date inválido: {options['start_date']}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if 'end_date' in options and isinstance(options['end_date'], str):
                try:
                    parsed_date = date_parse(options['end_date'])
                    # Asegurar timezone-aware
                    if timezone.is_naive(parsed_date):
                        parsed_date = timezone.make_aware(parsed_date)
                    options['end_date'] = parsed_date.replace(hour=23, minute=59, second=59)
                    logger.debug(f"Fecha fin parseada: {options['end_date']}")
                except Exception as e:
                    logger.error(f"Error parseando end_date '{options['end_date']}': {e}")
                    return Response(
                        {"error": f"Formato de end_date inválido: {options['end_date']}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Normalizar group_by (aceptar "categoria", "category", "categoría")
            if 'group_by' in options:
                group_by = options['group_by'].lower() if options['group_by'] else None
                if group_by in ['categoria', 'categoría']:
                    options['group_by'] = 'category'
                elif group_by == 'cliente':
                    options['group_by'] = 'user'
                elif group_by == 'producto':
                    options['group_by'] = 'product'
            
            # Normalizar module (aceptar "reseñas", "reseñas", "reviews")
            if 'module' in options:
                module = options['module'].lower() if options['module'] else None
                if module in ['reseñas', 'reviews']:
                    options['module'] = 'reseñas'
                elif module in ['pedidos', 'orders']:
                    options['module'] = 'ventas'
            
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
            
            # 🔧 FIX: Retornar archivo vacío según el formato solicitado (NO JSON)
            if options['format'] == 'json':
                return Response([], status=status.HTTP_200_OK)
            
            elif options['format'] == 'csv':
                # Generar CSV vacío con mensaje
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['Mensaje'])
                writer.writerow(['No se encontraron resultados para los filtros especificados'])
                
                response = HttpResponse(
                    output.getvalue(),
                    content_type='text/csv; charset=utf-8-sig'
                )
                response['Content-Disposition'] = 'attachment; filename="sin_resultados.csv"'
                logger.info("Retornando CSV vacío (sin resultados)")
                return response
            
            elif options['format'] == 'excel':
                # Generar Excel vacío con mensaje
                workbook = openpyxl.Workbook()
                sheet = workbook.active
                sheet.title = "Sin Resultados"
                sheet['A1'] = "No se encontraron resultados para los filtros especificados"
                
                output = io.BytesIO()
                workbook.save(output)
                output.seek(0)
                
                response = HttpResponse(
                    output.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = 'attachment; filename="sin_resultados.xlsx"'
                logger.info("Retornando Excel vacío (sin resultados)")
                return response
            
            elif options['format'] == 'pdf':
                # Generar PDF vacío con mensaje
                html_content = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
                        h1 { color: #666; }
                        p { color: #999; }
                    </style>
                </head>
                <body>
                    <h1>No se encontraron resultados</h1>
                    <p>Los filtros especificados no arrojaron datos.</p>
                </body>
                </html>
                """
                
                try:
                    from weasyprint import HTML
                    pdf_file = HTML(string=html_content).write_pdf()
                    response = HttpResponse(pdf_file, content_type='application/pdf')
                    response['Content-Disposition'] = 'attachment; filename="sin_resultados.pdf"'
                    logger.info("Retornando PDF vacío (sin resultados)")
                    return response
                except ImportError:
                    # Fallback si WeasyPrint no está disponible
                    response = HttpResponse(
                        "No se encontraron resultados para los filtros especificados.",
                        content_type='text/plain'
                    )
                    logger.warning("WeasyPrint no disponible, retornando texto plano")
                    return response
            
            else:
                # Fallback por si hay otro formato
                return Response(
                    {"message": "La consulta no arrojó resultados."},
                    status=status.HTTP_200_OK
                )

        # 3. Generar título descriptivo
        title = generate_report_title(options)
        
        # 4. Generar el archivo
        try:
            if options.get('format') == 'excel':
                logger.info("Generando reporte Excel...")
                return generate_excel_report(queryset, headers, title)
            
            elif options.get('format') == 'csv':
                logger.info("Generando reporte CSV...")
                return generate_csv_report(queryset, headers, title)
            
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
