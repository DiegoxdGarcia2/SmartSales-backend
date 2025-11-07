"""
Vista para generación de reportes por comando de voz.
Integra Gemini AI con capacidad multimodal para procesar audio.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser

from .ai_parser import parse_with_gemini_audio
from .query_builder import build_report_query
from .generators import generate_excel_report, generate_pdf_report, generate_csv_report
from .views import generate_report_title

logger = logging.getLogger(__name__)


class VoiceReportAPIView(APIView):
    """
    API View para generar reportes desde comandos de voz.
    
    POST /api/reports/voice_report/
    
    Body (multipart/form-data):
    {
        'audio': <archivo de audio WebM/WAV>,
        'format': 'pdf'  // Opcional: forzar formato
    }
    
    Permisos: Solo administradores
    
    Respuesta: Archivo de reporte (Excel/PDF/CSV) o JSON
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        logger.info('🎤 Recibida solicitud de reporte por voz')
        
        # Obtener archivo de audio
        audio_file = request.FILES.get('audio')
        format_override = request.data.get('format', None)
        
        if not audio_file:
            return Response(
                {'error': 'Se requiere un archivo de audio.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Leer bytes del audio
            audio_data = audio_file.read()
            mime_type = audio_file.content_type or 'audio/webm'
            
            logger.info(f'📥 Audio recibido: {len(audio_data)} bytes, tipo: {mime_type}')
            
            # Parsear con Gemini AI (audio → JSON)
            logger.info('🤖 Procesando audio con Gemini AI...')
            options = parse_with_gemini_audio(audio_data, mime_type)
            
            if options.get('errors'):
                logger.warning(f'⚠️ Gemini Audio falló: {options.get("errors")}')
                return Response(
                    {'error': f'No se pudo procesar el audio: {options.get("errors")}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f'✅ Audio parseado exitosamente: {options}')
            
            # Override de formato si se especificó
            if format_override and format_override in ['pdf', 'excel', 'json', 'csv']:
                options['format'] = format_override
            
            # Guardar prompt original (transcripción aproximada)
            options['original_prompt'] = f'Comando de voz: {options.get("module", "reporte")}'
            
        except Exception as e:
            logger.error(f'❌ Error al procesar audio: {e}', exc_info=True)
            return Response(
                {'error': f'Error al procesar el audio: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # A partir de aquí, usar la misma lógica que DynamicReportAPIView
        try:
            queryset, headers = build_report_query(options)
        except Exception as e:
            logger.error(f'Error en Query Builder para audio: {e}', exc_info=True)
            return Response(
                {'error': f'Error al construir la consulta: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if queryset is None:
            return Response(
                {'error': f'El módulo "{options.get("module")}" no está soportado.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not queryset.exists():
            logger.info('Reporte por voz no arrojó resultados.')
            return Response(
                {'message': 'No se encontraron resultados para el comando de voz.'},
                status=status.HTTP_200_OK
            )
        
        # Generar título descriptivo
        title = generate_report_title(options)
        
        # Generar el archivo según formato
        try:
            if options.get('format') == 'excel':
                logger.info('Generando reporte Excel desde voz...')
                return generate_excel_report(queryset, headers, title)
            
            elif options.get('format') == 'csv':
                logger.info('Generando reporte CSV desde voz...')
                return generate_csv_report(queryset, headers, title)
            
            elif options.get('format') == 'pdf':
                logger.info('Generando reporte PDF desde voz...')
                record_count = queryset.count()
                logger.info(f'📄 PDF desde voz con {record_count} registros')
                return generate_pdf_report(queryset, headers, title, options.get('original_prompt', 'Reporte por voz'))
            
            else:  # 'json'
                logger.info('Generando respuesta JSON desde voz...')
                return Response(list(queryset), status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f'Error al generar archivo desde voz: {e}', exc_info=True)
            return Response(
                {'error': f'Error al generar el archivo: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
