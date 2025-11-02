"""
Parser avanzado de prompts para reportes dinámicos.
Convierte texto en lenguaje natural a parámetros estructurados.
"""
import re
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from dateutil.parser import parse as date_parse
from dateutil.relativedelta import relativedelta

# Importar modelos para obtener nombres de filtros dinámicamente
from products.models import Category, Brand
from users.models import User

logger = logging.getLogger(__name__)

# ============================================================================
# DEFINICIÓN DE PATRONES (Regex)
# ============================================================================

# Formato de salida: pdf, excel, csv
FORMAT_REGEX = re.compile(r'\b(pdf|excel|csv)\b', re.IGNORECASE)

# Módulo del reporte: ventas, productos, clientes, reseñas, pedidos
MODULE_REGEX = re.compile(r'\b(ventas|productos|clientes|reseñas|pedidos)\b', re.IGNORECASE)

# Agrupación: por cliente, producto, categoría, marca, mes
GROUP_BY_REGEX = re.compile(r'agrupado por (cliente|producto|categoria|marca|mes)', re.IGNORECASE)

# --- Patrones de Fecha ---
YEAR_REGEX = re.compile(r'\b(del año|en el año|del|en) (202[3-9])\b', re.IGNORECASE)
MONTH_YEAR_REGEX = re.compile(r'\b(de|en) (\w+) (202[3-9])\b', re.IGNORECASE)  # "de octubre 2024"
LAST_X_DAYS_REGEX = re.compile(r'últimos (\d+|treinta) días', re.IGNORECASE)
LAST_X_MONTHS_REGEX = re.compile(r'últimos (\d+|seis|doce) meses', re.IGNORECASE)
TODAY_REGEX = re.compile(r'\b(hoy)\b', re.IGNORECASE)
YESTERDAY_REGEX = re.compile(r'\b(ayer)\b', re.IGNORECASE)

# --- Patrones de Filtros (Texto) ---
# Captura "texto entre comillas" o una_palabra_sin_espacios
BRAND_REGEX = re.compile(r'\b(de la marca|marca) (?:"([^"]*)"|(\S+))\b', re.IGNORECASE)
CATEGORY_REGEX = re.compile(r'\b(de la categoria|categoria) (?:"([^"]*)"|(\S+))\b', re.IGNORECASE)
CLIENT_REGEX = re.compile(r'\b(del cliente|cliente) (?:"([^"]*)"|(\S+))\b', re.IGNORECASE)

# ============================================================================
# MAPAS DE CONVERSIÓN
# ============================================================================

MONTH_MAP_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

NUMBER_MAP = {
    'treinta': 30,
    'seis': 6,
    'doce': 12
}


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _get_number(value_str):
    """
    Convierte texto numérico a entero.
    Ej: "treinta" -> 30, "6" -> 6
    """
    return NUMBER_MAP.get(value_str.lower()) or int(value_str)


def _parse_dates(text, now):
    """
    Parsea expresiones de fechas del texto.
    Retorna tupla (start_date, end_date) o (None, None).
    
    También soporta rangos explícitos con 'del X al Y' o 'desde X hasta Y'
    donde X e Y pueden ser fechas en formato natural o ISO.
    """
    try:
        # Intentar parsear rango explícito: "del 01/01/2024 al 31/03/2024" o "desde X hasta Y"
        range_pattern = re.compile(
            r'(del|desde)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2})\s+(al|hasta)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2})',
            re.IGNORECASE
        )
        if (match := range_pattern.search(text)):
            try:
                start_str = match.group(2)
                end_str = match.group(4)
                
                # Parsear con dateutil (acepta múltiples formatos)
                start_date = date_parse(start_str, dayfirst=True)
                end_date = date_parse(end_str, dayfirst=True)
                
                # Asegurar que sean timezone-aware
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
                
                # Ajustar horas
                start_date = start_date.replace(hour=0, minute=0, second=0)
                end_date = end_date.replace(hour=23, minute=59, second=59)
                
                logger.debug(f"Fecha parseada: Rango explícito ({start_date} a {end_date})")
                return start_date, end_date
            except Exception as e:
                logger.warning(f"Error parseando rango de fechas explícito: {e}")
        
        # Últimos X días
        if (match := LAST_X_DAYS_REGEX.search(text)):
            days = _get_number(match.group(1))
            end_date = now.replace(hour=23, minute=59, second=59)
            start_date = (now - timedelta(days=days-1)).replace(hour=0, minute=0, second=0)
            logger.debug(f"Fecha parseada: Últimos {days} días ({start_date} a {end_date})")
            return start_date, end_date
        
        # Últimos X meses
        if (match := LAST_X_MONTHS_REGEX.search(text)):
            months = _get_number(match.group(1))
            end_date = now.replace(hour=23, minute=59, second=59)
            start_date = (now - relativedelta(months=months)).replace(day=1, hour=0, minute=0, second=0)
            logger.debug(f"Fecha parseada: Últimos {months} meses ({start_date} a {end_date})")
            return start_date, end_date
        
        # Hoy
        if TODAY_REGEX.search(text):
            start_date = now.replace(hour=0, minute=0, second=0)
            end_date = now.replace(hour=23, minute=59, second=59)
            logger.debug(f"Fecha parseada: Hoy ({start_date} a {end_date})")
            return start_date, end_date
        
        # Ayer
        if YESTERDAY_REGEX.search(text):
            yesterday = now - timedelta(days=1)
            start_date = yesterday.replace(hour=0, minute=0, second=0)
            end_date = yesterday.replace(hour=23, minute=59, second=59)
            logger.debug(f"Fecha parseada: Ayer ({start_date} a {end_date})")
            return start_date, end_date
        
        # Mes específico + año (ej: "octubre 2024")
        if (match := MONTH_YEAR_REGEX.search(text)):
            month_name = match.group(2).lower()
            year = int(match.group(3))
            month_num = MONTH_MAP_ES.get(month_name)
            
            if month_num:
                start_date = timezone.make_aware(datetime(year, month_num, 1))
                end_date = (start_date + relativedelta(months=1)) - timedelta(seconds=1)
                logger.debug(f"Fecha parseada: {month_name} {year} ({start_date} a {end_date})")
                return start_date, end_date
        
        # Año completo
        if (match := YEAR_REGEX.search(text)):
            year = int(match.group(2))
            start_date = timezone.make_aware(datetime(year, 1, 1))
            end_date = timezone.make_aware(datetime(year, 12, 31, 23, 59, 59))
            logger.debug(f"Fecha parseada: Año {year} ({start_date} a {end_date})")
            return start_date, end_date
        
        # TODO: Añadir regex para rangos explícitos "del DD/MM/YYYY al DD/MM/YYYY"
        
    except Exception as e:
        logger.error(f"Error parseando fechas del prompt: {e}", exc_info=True)
    
    return None, None


def _find_entity_match(text, regex):
    """
    Encuentra coincidencia de entidad en el texto.
    Retorna el texto capturado (entre comillas o sin espacios).
    """
    match = regex.search(text)
    if match:
        # El grupo 2 es para "texto entre comillas", el 3 es para texto_sin_espacios
        return match.group(2) or match.group(3)
    return None


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def parse_report_prompt(prompt_text: str):
    """
    Parsea un prompt en lenguaje natural y extrae parámetros estructurados.
    
    Args:
        prompt_text: Texto del prompt (ej: "reporte de ventas de Samsung para octubre 2024 en pdf")
    
    Returns:
        dict: Diccionario con opciones parseadas:
            - original_prompt: Texto original
            - format: 'pdf', 'excel', 'json'
            - module: 'ventas', 'productos', 'clientes', 'reseñas'
            - start_date: datetime o None
            - end_date: datetime o None
            - group_by: 'category', 'brand', 'user', 'product', 'mes' o None
            - filters: dict con filtros de texto (brand_name, category_name, user_username)
            - errors: lista de errores encontrados
    
    Examples:
        >>> parse_report_prompt("ventas de Samsung en octubre 2024 en pdf")
        {
            'format': 'pdf',
            'module': 'ventas',
            'filters': {'brand_name': 'Samsung'},
            'start_date': datetime(...),
            'end_date': datetime(...),
            ...
        }
    """
    logger.info(f"Parseando prompt: '{prompt_text}'")
    
    # Inicializar opciones con valores por defecto
    options = {
        'original_prompt': prompt_text,
        'format': 'json',          # Formato por defecto
        'module': 'ventas',         # Módulo por defecto
        'start_date': None,
        'end_date': None,
        'group_by': None,
        'filters': {},              # Diccionario para filtros
        'errors': []
    }
    
    text = prompt_text.lower()
    
    # 1. Parsear Formato de Salida
    if (match := FORMAT_REGEX.search(text)):
        options['format'] = match.group(1).lower()
        # ✅ Mantener CSV como formato independiente (ya no se convierte a excel)
        logger.debug(f"Formato detectado: {options['format']}")
    
    # 2. Parsear Módulo del Reporte
    if (match := MODULE_REGEX.search(text)):
        module = match.group(1).lower()
        # Normalizar "pedidos" a "ventas"
        options['module'] = 'ventas' if module == 'pedidos' else module
        logger.debug(f"Módulo detectado: {options['module']}")
    
    # 3. Parsear Agrupación
    if (match := GROUP_BY_REGEX.search(text)):
        group = match.group(1).lower()
        # Normalizar nombres de agrupación
        if group == 'categoria':
            group = 'category'
        elif group == 'cliente':
            group = 'user'
        elif group == 'producto':
            group = 'product'
        
        options['group_by'] = group
        logger.debug(f"Agrupación detectada: {options['group_by']}")
    
    # 4. Parsear Fechas
    now = timezone.now()
    start_date, end_date = _parse_dates(text, now)
    if start_date:
        options['start_date'] = start_date
        options['end_date'] = end_date
    
    # 5. Parsear Filtros de Texto
    
    # Filtro por Marca
    if (brand_name := _find_entity_match(text, BRAND_REGEX)):
        options['filters']['brand_name'] = brand_name
        logger.debug(f"Filtro por marca encontrado: {brand_name}")
    
    # Filtro por Categoría
    if (category_name := _find_entity_match(text, CATEGORY_REGEX)):
        options['filters']['category_name'] = category_name
        logger.debug(f"Filtro por categoría encontrado: {category_name}")
    
    # Filtro por Cliente (username)
    if (client_name := _find_entity_match(text, CLIENT_REGEX)):
        options['filters']['user_username'] = client_name
        logger.debug(f"Filtro por cliente encontrado: {client_name}")
    
    logger.info(f"Opciones parseadas exitosamente: {options}")
    return options
