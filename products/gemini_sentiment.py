"""
Servicio de análisis de sentimiento avanzado usando Google Gemini AI.
Reemplaza VADER con análisis contextual en español y extracción de aspectos.
"""

import logging
import json
import google.generativeai as genai
from django.conf import settings
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Configurar Gemini API
genai.configure(api_key=settings.GOOGLE_AI_API_KEY)


class GeminiSentimentAnalyzer:
    """
    Analizador de sentimiento avanzado usando Google Gemini 2.5 Flash.
    Proporciona análisis multi-dimensional de reseñas en español.
    """
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Configuración de seguridad para no bloquear contenido legítimo
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        # Configuración de generación
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.1,  # Baja temperatura para respuestas consistentes
            max_output_tokens=500,
        )
    
    def analyze_review(
        self, 
        rating: int, 
        comment: str, 
        product_name: Optional[str] = None
    ) -> Dict:
        """
        Analiza una reseña y retorna análisis multi-dimensional.
        
        Args:
            rating: Calificación numérica (1-5)
            comment: Texto del comentario
            product_name: Nombre del producto (opcional, mejora contexto)
        
        Returns:
            Dict con:
                - sentiment: 'POSITIVO', 'NEUTRO', 'NEGATIVO'
                - confidence: float 0-1
                - aspects: Dict con análisis de aspectos específicos
                - summary: Resumen breve del sentimiento
                - keywords: Palabras clave extraídas
        """
        
        # Si no hay comentario, análisis simple basado en rating
        if not comment or not comment.strip():
            return self._analyze_rating_only(rating)
        
        try:
            # Construir prompt estructurado
            prompt = self._build_analysis_prompt(rating, comment, product_name)
            
            # Llamar a Gemini
            response = self.model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                generation_config=self.generation_config
            )
            
            # Parsear respuesta JSON
            try:
                result = json.loads(response.text)
                
                # Validar y normalizar resultado
                return self._normalize_result(result, rating)
                
            except json.JSONDecodeError:
                logger.warning(f"Gemini no retornó JSON válido. Respuesta: {response.text[:200]}")
                return self._analyze_rating_only(rating)
        
        except Exception as e:
            logger.error(f"Error en análisis de sentimiento con Gemini: {e}", exc_info=True)
            # Fallback: análisis basado solo en rating
            return self._analyze_rating_only(rating)
    
    def _build_analysis_prompt(
        self, 
        rating: int, 
        comment: str, 
        product_name: Optional[str]
    ) -> str:
        """
        Construye el prompt para Gemini con contexto estructurado.
        """
        product_context = f' del producto "{product_name}"' if product_name else ''
        
        prompt = f"""Analiza la siguiente reseña{product_context} en español y proporciona un análisis detallado.

**RESEÑA:**
- Calificación: {rating}/5 estrellas
- Comentario: "{comment}"

**INSTRUCCIONES:**
Responde ÚNICAMENTE con un objeto JSON válido (sin markdown, sin explicaciones adicionales) con la siguiente estructura:

{{
    "sentiment": "<POSITIVO|NEUTRO|NEGATIVO>",
    "confidence": <número entre 0 y 1>,
    "aspects": {{
        "product_quality": <número entre 1 y 5>,
        "value_for_money": <número entre 1 y 5>,
        "delivery_experience": <número entre 1 y 5 o null si no se menciona>
    }},
    "summary": "<resumen breve en una oración del sentimiento>",
    "keywords": ["<palabra1>", "<palabra2>", "<palabra3>"]
}}

**CRITERIOS:**
- "sentiment": Debe ser POSITIVO (rating ≥4 y comentario positivo), NEGATIVO (rating ≤2 y comentario negativo), o NEUTRO (casos intermedios o contradictorios)
- "confidence": Qué tan seguro estás del análisis (1.0 = muy seguro, 0.5 = incierto)
- "aspects": Evalúa cada aspecto del 1 al 5 basándote en el comentario. Si no se menciona un aspecto, usa null.
- "summary": Máximo 100 caracteres, describe el sentimiento principal
- "keywords": 3-5 palabras clave relevantes mencionadas en el comentario

Responde SOLO con el JSON, sin texto adicional."""
        
        return prompt
    
    def _normalize_result(self, result: Dict, rating: int) -> Dict:
        """
        Valida y normaliza el resultado de Gemini.
        """
        # Normalizar sentimiento
        sentiment = result.get('sentiment', '').upper()
        if sentiment not in ['POSITIVO', 'NEUTRO', 'NEGATIVO']:
            # Fallback basado en rating
            if rating >= 4:
                sentiment = 'POSITIVO'
            elif rating <= 2:
                sentiment = 'NEGATIVO'
            else:
                sentiment = 'NEUTRO'
        
        # Validar confidence
        confidence = result.get('confidence', 0.8)
        if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
            confidence = 0.8
        
        # Validar aspects
        aspects = result.get('aspects', {})
        if not isinstance(aspects, dict):
            aspects = {}
        
        # Validar cada aspecto
        for key in ['product_quality', 'value_for_money', 'delivery_experience']:
            value = aspects.get(key)
            if value is not None:
                if not isinstance(value, (int, float)) or not (1 <= value <= 5):
                    aspects[key] = None
        
        # Validar summary
        summary = result.get('summary', 'Reseña analizada')
        if not isinstance(summary, str):
            summary = 'Reseña analizada'
        summary = summary[:200]  # Limitar longitud
        
        # Validar keywords
        keywords = result.get('keywords', [])
        if not isinstance(keywords, list):
            keywords = []
        keywords = [str(k)[:50] for k in keywords[:10]]  # Máximo 10 keywords, 50 chars cada una
        
        return {
            'sentiment': sentiment,
            'confidence': round(float(confidence), 2),
            'aspects': aspects,
            'summary': summary,
            'keywords': keywords
        }
    
    def _analyze_rating_only(self, rating: int) -> Dict:
        """
        Análisis fallback basado solo en el rating cuando no hay comentario
        o cuando Gemini falla.
        """
        if rating >= 4:
            sentiment = 'POSITIVO'
            summary = f"Calificación alta ({rating}/5)"
        elif rating <= 2:
            sentiment = 'NEGATIVO'
            summary = f"Calificación baja ({rating}/5)"
        else:
            sentiment = 'NEUTRO'
            summary = f"Calificación media ({rating}/5)"
        
        return {
            'sentiment': sentiment,
            'confidence': 0.7,  # Confianza moderada sin comentario
            'aspects': {
                'product_quality': rating,
                'value_for_money': rating,
                'delivery_experience': None
            },
            'summary': summary,
            'keywords': []
        }


# Instancia global del analizador (singleton)
_analyzer_instance = None


def get_sentiment_analyzer() -> GeminiSentimentAnalyzer:
    """
    Obtiene la instancia singleton del analizador de sentimiento.
    """
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = GeminiSentimentAnalyzer()
    return _analyzer_instance


def analyze_review_sentiment_advanced(
    rating: int, 
    comment: str,
    product_name: Optional[str] = None
) -> Dict:
    """
    Función principal para analizar sentimiento de reseñas.
    
    Args:
        rating: Calificación 1-5
        comment: Texto del comentario
        product_name: Nombre del producto (opcional)
    
    Returns:
        Dict con análisis completo
    """
    analyzer = get_sentiment_analyzer()
    return analyzer.analyze_review(rating, comment, product_name)


def extract_basic_sentiment(analysis: Dict) -> Tuple[str, float]:
    """
    Extrae sentimiento y score básico del análisis avanzado
    para compatibilidad con código existente.
    
    Args:
        analysis: Dict retornado por analyze_review_sentiment_advanced
    
    Returns:
        Tuple (sentiment, score) donde:
            - sentiment: 'POSITIVO', 'NEUTRO', 'NEGATIVO'
            - score: float entre -1 y 1 (compatible con VADER)
    """
    sentiment = analysis.get('sentiment', 'NEUTRO')
    confidence = analysis.get('confidence', 0.5)
    
    # Convertir a score estilo VADER (-1 a 1)
    if sentiment == 'POSITIVO':
        score = 0.5 + (confidence * 0.5)  # 0.5 a 1.0
    elif sentiment == 'NEGATIVO':
        score = -0.5 - (confidence * 0.5)  # -1.0 a -0.5
    else:  # NEUTRO
        score = (confidence - 0.5) * 0.2  # -0.1 a 0.1
    
    return sentiment, round(score, 2)
