"""
Parser de lenguaje natural usando Google Gemini AI.

Este módulo utiliza Gemini 1.5 Pro para convertir prompts en lenguaje natural
a estructuras JSON para generar reportes dinámicos.
"""

from django.conf import settings
import json
import logging
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

# NO importar genai aquí - hacerlo lazy para evitar OOM en Render
# import google.generativeai as genai

# System prompt optimizado para Gemini
SYSTEM_PROMPT = """
Eres un asistente para SmartSales que convierte solicitudes de reportes en JSON estructurado.

REGLAS ESTRICTAS:
1. SIEMPRE responde SOLO con JSON válido, sin texto adicional antes o después
2. NO uses markdown (```json), solo el JSON puro
3. Usa exactamente los nombres de campos especificados

MÓDULOS DISPONIBLES:
- "ventas": Reportes de ventas/órdenes (OrderItem)
- "productos": Catálogo de productos
- "clientes": Lista de usuarios/clientes  
- "reseñas": Reviews de productos

FORMATOS VÁLIDOS:
- "excel": Archivo Excel (.xlsx)
- "pdf": Documento PDF
- "csv": Archivo CSV

AGRUPACIÓN (group_by) - OPCIONAL:
- null: Sin agrupar (detallado)
- "categoria": Agrupar por categoría de producto
- "marca": Agrupar por marca
- "producto": Agrupar por producto específico
- "cliente": Agrupar por cliente
- "mes": Agrupar por mes

FECHAS:
- Formato: "YYYY-MM-DD"
- Si no se especifica fecha: null
- Ejemplos de conversión:
  * "octubre 2024" → start: "2024-10-01", end: "2024-10-31"
  * "mes pasado" → calcula desde el mes anterior completo
  * "últimos 30 días" → desde hace 30 días hasta hoy
  * "este año" → desde enero 1 hasta hoy
  * "2024" → desde "2024-01-01" hasta "2024-12-31"
  * "noviembre" (sin año) → usa año actual

FILTROS - OPCIONAL (dict vacío {} si no hay):
- brand_name: nombre de marca (ejemplo: "Samsung", "Apple", "Sony")
- category_name: categoría (ejemplo: "Smartphones", "Laptops", "Tablets")
- product_name: nombre específico de producto
- client_name: nombre de cliente

ESTRUCTURA JSON REQUERIDA:
{{
  "module": "ventas",
  "format": "excel",
  "start_date": "2024-10-01",
  "end_date": "2024-10-31",
  "filters": {{
    "brand_name": "Samsung"
  }},
  "group_by": "categoria"
}}

EJEMPLOS DE CONVERSIÓN:

Ejemplo 1:
Input: "ventas de octubre en excel"
Output: {{"module": "ventas", "format": "excel", "start_date": "2024-10-01", "end_date": "2024-10-31", "filters": {{}}, "group_by": null}}

Ejemplo 2:
Input: "productos samsung en pdf"
Output: {{"module": "productos", "format": "pdf", "start_date": null, "end_date": null, "filters": {{"brand_name": "Samsung"}}, "group_by": null}}

Ejemplo 3:
Input: "dame las ventas de los últimos 7 días agrupadas por marca en excel"
Output: {{"module": "ventas", "format": "excel", "start_date": "CALCULA_HACE_7_DIAS", "end_date": "HOY", "filters": {{}}, "group_by": "marca"}}

Ejemplo 4:
Input: "reporte de clientes en csv"
Output: {{"module": "clientes", "format": "csv", "start_date": null, "end_date": null, "filters": {{}}, "group_by": null}}

Ejemplo 5:
Input: "reseñas de laptops del 2024 en pdf"
Output: {{"module": "reseñas", "format": "pdf", "start_date": "2024-01-01", "end_date": "2024-12-31", "filters": {{"category_name": "Laptops"}}, "group_by": null}}

IMPORTANTE:
- Si no entiendes algo, usa valores razonables por defecto
- Si no se especifica formato, usa "excel"
- Si no se especifica fecha, usa null
- Siempre incluye el campo "filters" (aunque sea {{}})
- Siempre incluye el campo "group_by" (aunque sea null)

FECHA ACTUAL PARA CONTEXTO: {current_date}
"""


def parse_with_gemini(user_prompt: str) -> dict:
    """
    Parsea un prompt de lenguaje natural usando Google Gemini.
    
    Args:
        user_prompt: Texto del usuario (ej: "ventas de octubre en excel")
        
    Returns:
        dict con estructura:
        {
            'module': str,           # 'ventas', 'productos', 'clientes', 'reseñas'
            'format': str,           # 'excel', 'pdf', 'csv'
            'start_date': str|None,  # 'YYYY-MM-DD' o None
            'end_date': str|None,    # 'YYYY-MM-DD' o None
            'filters': dict,         # {'brand_name': 'Samsung', ...}
            'group_by': str|None,    # 'categoria', 'marca', 'producto', 'cliente', 'mes', None
            'errors': list           # Lista de errores si los hay
        }
    
    Raises:
        Exception: Si hay error en la comunicación con Gemini
    """
    try:
        logger.info(f"🤖 Parseando con Gemini AI: '{user_prompt}'")
        
        # Lazy import para evitar OOM en Render durante startup
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        
        # Usar Gemini 2.5 Flash (modelo estable, rápido y con soporte multimodal)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Fecha actual para contexto
        current_date = timezone.now().strftime("%Y-%m-%d")
        # Reemplazar manualmente para evitar conflicto con {{ }}
        prompt = SYSTEM_PROMPT.replace('{current_date}', current_date)
        
        # Generar respuesta
        response = model.generate_content(
            f"{prompt}\n\nInput del usuario: {user_prompt}\n\nOutput JSON:",
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,  # Respuestas consistentes y precisas
                top_p=0.95,
                top_k=40,
                max_output_tokens=1024,
            )
        )
        
        # Obtener texto de respuesta
        result_text = response.text.strip()
        logger.info(f"✅ Respuesta de Gemini: {result_text[:200]}...")
        
        # Limpiar markdown si existe
        if result_text.startswith('```json'):
            result_text = result_text.replace('```json', '').replace('```', '').strip()
        elif result_text.startswith('```'):
            result_text = result_text.replace('```', '').strip()
        
        # Parse JSON
        result = json.loads(result_text)
        
        # Validar campos requeridos
        if 'module' not in result:
            logger.warning("⚠️ Gemini no retornó el campo 'module'")
            return {
                'module': None,
                'format': 'excel',
                'start_date': None,
                'end_date': None,
                'filters': {},
                'group_by': None,
                'errors': ['No se pudo determinar el módulo del reporte']
            }
        
        if 'format' not in result:
            logger.warning("⚠️ Gemini no retornó el campo 'format', usando 'excel' por defecto")
            result['format'] = 'excel'
        
        # Asegurar estructura completa
        parsed_result = {
            'module': result.get('module'),
            'format': result.get('format', 'excel'),
            'start_date': result.get('start_date'),
            'end_date': result.get('end_date'),
            'filters': result.get('filters', {}),
            'group_by': result.get('group_by'),
            'errors': []
        }
        
        logger.info(f"✅ Parsing exitoso: module={parsed_result['module']}, format={parsed_result['format']}")
        return parsed_result
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parseando JSON de Gemini: {str(e)}")
        logger.error(f"Respuesta recibida: {result_text}")
        return {
            'module': None,
            'format': 'excel',
            'start_date': None,
            'end_date': None,
            'filters': {},
            'group_by': None,
            'errors': [f'Error parseando la respuesta de Gemini: {str(e)}']
        }
    except Exception as e:
        logger.error(f"❌ Error llamando a Gemini API: {str(e)}")
        return {
            'module': None,
            'format': 'excel',
            'start_date': None,
            'end_date': None,
            'filters': {},
            'group_by': None,
            'errors': [f'Error comunicándose con Gemini: {str(e)}']
        }


def parse_with_gemini_audio(audio_data: bytes, mime_type: str = "audio/webm") -> dict:
    """
    Parsea audio directo usando Gemini (capacidad multimodal).
    
    Esta función permite procesar audio de entrada de voz directamente
    sin necesidad de transcribirlo primero con Web Speech API.
    
    Args:
        audio_data: Bytes del archivo de audio
        mime_type: Tipo MIME del audio (default: "audio/webm")
        
    Returns:
        dict con la misma estructura que parse_with_gemini()
        
    Note:
        Esta es una característica avanzada de Gemini 1.5 Pro.
        Útil para integración con entrada de voz en la Fase 7.
    """
    try:
        logger.info(f"🎤 Parseando audio con Gemini AI (mime_type: {mime_type})")
        
        # Lazy import para evitar OOM en Render durante startup
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        current_date = timezone.now().strftime("%Y-%m-%d")
        prompt = SYSTEM_PROMPT.replace('{current_date}', current_date)
        
        # Gemini puede procesar audio + texto en una sola llamada
        response = model.generate_content([
            {"mime_type": mime_type, "data": audio_data},
            f"{prompt}\n\nTranscribe el audio y conviértelo a JSON:"
        ])
        
        result_text = response.text.strip()
        
        # Limpiar markdown
        if result_text.startswith('```json'):
            result_text = result_text.replace('```json', '').replace('```', '').strip()
        elif result_text.startswith('```'):
            result_text = result_text.replace('```', '').strip()
        
        result = json.loads(result_text)
        
        return {
            'module': result.get('module'),
            'format': result.get('format', 'excel'),
            'start_date': result.get('start_date'),
            'end_date': result.get('end_date'),
            'filters': result.get('filters', {}),
            'group_by': result.get('group_by'),
            'errors': []
        }
        
    except Exception as e:
        logger.error(f"❌ Error procesando audio con Gemini: {str(e)}")
        return {
            'module': None,
            'format': 'excel',
            'start_date': None,
            'end_date': None,
            'filters': {},
            'group_by': None,
            'errors': [f'Error procesando audio: {str(e)}']
        }
