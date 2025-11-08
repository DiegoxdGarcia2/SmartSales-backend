"""
Comando Django para migrar reseñas existentes al análisis avanzado con Gemini.
Analiza reseñas que solo tienen análisis básico (VADER) y las actualiza con Gemini.
"""

import logging
from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import Review
from products.gemini_sentiment import analyze_review_sentiment_advanced, extract_basic_sentiment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migra reseñas existentes al análisis avanzado con Gemini AI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar reanálisis de todas las reseñas, incluso las que ya tienen análisis avanzado',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limitar el número de reseñas a procesar',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        limit = options.get('limit')
        
        self.stdout.write('=' * 70)
        self.stdout.write('🚀 MIGRACIÓN A ANÁLISIS AVANZADO CON GEMINI AI')
        self.stdout.write('=' * 70)
        
        # Buscar reseñas que necesitan migración
        self.stdout.write('\n📊 Buscando reseñas para migrar...')
        
        if force:
            # Reanalizar todas
            reviews_to_migrate = Review.objects.all().select_related('product', 'user')
            self.stdout.write('⚠️  Modo FORCE activado: reanalizando TODAS las reseñas')
        else:
            # Solo reseñas sin análisis avanzado
            reviews_to_migrate = Review.objects.filter(
                Q(sentiment_confidence__isnull=True) |  # Sin confianza
                Q(sentiment_summary__isnull=True) | Q(sentiment_summary='')  # Sin resumen
            ).select_related('product', 'user')
        
        if limit:
            reviews_to_migrate = reviews_to_migrate[:limit]
            self.stdout.write(f'📏 Limitando a {limit} reseñas')
        
        total_reviews = reviews_to_migrate.count()
        
        if total_reviews == 0:
            self.stdout.write(self.style.SUCCESS('✅ No hay reseñas pendientes de migración.'))
            return
        
        self.stdout.write(f'✅ Encontradas {total_reviews} reseñas para migrar.')
        
        # Procesar reseñas
        self.stdout.write('\n🤖 Analizando con Gemini AI...')
        
        updated_count = 0
        error_count = 0
        sentiments_counter = {'POSITIVO': 0, 'NEUTRO': 0, 'NEGATIVO': 0}
        
        for idx, review in enumerate(reviews_to_migrate, 1):
            try:
                # Analizar con Gemini
                analysis = analyze_review_sentiment_advanced(
                    rating=review.rating,
                    comment=review.comment or '',
                    product_name=review.product.name
                )
                
                # Extraer datos
                sentiment, sentiment_score = extract_basic_sentiment(analysis)
                sentiment_confidence = analysis.get('confidence', 0.8)
                sentiment_summary = analysis.get('summary', '')
                aspects = analysis.get('aspects', {})
                keywords = analysis.get('keywords', [])
                
                # Actualizar reseña
                review.sentiment = sentiment
                review.sentiment_score = sentiment_score
                review.sentiment_confidence = sentiment_confidence
                review.sentiment_summary = sentiment_summary
                review.aspect_quality = aspects.get('product_quality')
                review.aspect_value = aspects.get('value_for_money')
                review.aspect_delivery = aspects.get('delivery_experience')
                review.keywords = keywords if keywords else None
                
                review.save(update_fields=[
                    'sentiment', 'sentiment_score', 'sentiment_confidence',
                    'sentiment_summary', 'aspect_quality', 'aspect_value',
                    'aspect_delivery', 'keywords'
                ])
                
                updated_count += 1
                sentiments_counter[sentiment] += 1
                
                # Mostrar progreso cada 10 reseñas
                if idx % 10 == 0:
                    self.stdout.write(f'   Procesadas: {idx}/{total_reviews}... ({updated_count} actualizadas)')
            
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Error al migrar reseña ID {review.id}: {e}",
                    exc_info=True
                )
                self.stdout.write(
                    self.style.ERROR(f'❌ Error en reseña ID {review.id}: {str(e)[:80]}')
                )
        
        # Resumen final
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('✅ MIGRACIÓN COMPLETADA'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'📊 Resumen:')
        self.stdout.write(f'  - Total de reseñas procesadas: {total_reviews}')
        self.stdout.write(f'  - Reseñas actualizadas: {updated_count}')
        
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'  - Errores encontrados: {error_count}'))
        
        self.stdout.write(f'\n📈 Distribución de sentimientos:')
        if updated_count > 0:
            self.stdout.write(f'  - Positivas: {sentiments_counter["POSITIVO"]} '
                             f'({sentiments_counter["POSITIVO"]/updated_count*100:.1f}%)')
            self.stdout.write(f'  - Neutras: {sentiments_counter["NEUTRO"]} '
                             f'({sentiments_counter["NEUTRO"]/updated_count*100:.1f}%)')
            self.stdout.write(f'  - Negativas: {sentiments_counter["NEGATIVO"]} '
                             f'({sentiments_counter["NEGATIVO"]/updated_count*100:.1f}%)')
        self.stdout.write('=' * 70)
