"""
Comando Django para analizar el sentimiento de todas las reseñas existentes.
Actualiza las reseñas que aún no tienen análisis de sentimiento.
"""

import logging
from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import Review
from products.views import analyze_review_sentiment

# Configurar logger
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Analiza el sentimiento de todas las reseñas existentes que no lo tengan.'

    def handle(self, *args, **options):
        """
        Ejecuta el análisis de sentimiento en reseñas existentes.
        """
        self.stdout.write('=' * 70)
        self.stdout.write('🔍 ANÁLISIS DE SENTIMIENTO DE RESEÑAS EXISTENTES')
        self.stdout.write('=' * 70)
        
        # Buscar reseñas sin análisis de sentimiento
        self.stdout.write('\n📊 Buscando reseñas sin análisis...')
        
        reviews_to_analyze = Review.objects.filter(
            Q(sentiment__isnull=True) |  # Reseñas sin sentimiento asignado
            Q(sentiment='')  # Reseñas con sentimiento vacío
        ).select_related('product', 'user')
        
        total_reviews = reviews_to_analyze.count()
        
        if total_reviews == 0:
            self.stdout.write(self.style.WARNING('⚠️  No hay reseñas pendientes de análisis.'))
            self.stdout.write('   Todas las reseñas ya tienen sentimiento asignado.')
            return
        
        self.stdout.write(f'✅ Encontradas {total_reviews} reseñas para analizar.')
        
        # Analizar y actualizar reseñas
        self.stdout.write('\n🤖 Analizando sentimientos...')
        
        updated_count = 0
        error_count = 0
        sentiments_counter = {'POSITIVO': 0, 'NEUTRO': 0, 'NEGATIVO': 0}
        
        for review in reviews_to_analyze:
            try:
                # Analizar sentimiento
                sentiment, score = analyze_review_sentiment(review.rating, review.comment)
                
                # Actualizar solo si cambió
                if review.sentiment != sentiment or review.sentiment_score != score:
                    review.sentiment = sentiment
                    review.sentiment_score = score
                    review.save(update_fields=['sentiment', 'sentiment_score'])
                    updated_count += 1
                    sentiments_counter[sentiment] += 1
                    
                    # Mostrar progreso cada 100 reseñas
                    if updated_count % 100 == 0:
                        self.stdout.write(f'   Procesadas: {updated_count}/{total_reviews}...')
            
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Error al analizar reseña ID {review.id} "
                    f"(Producto: {review.product.id}, Usuario: {review.user.id}): {e}",
                    exc_info=True
                )
                self.stdout.write(
                    self.style.ERROR(f'❌ Error en reseña ID {review.id}: {str(e)[:50]}')
                )
        
        # Resumen final
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('✅ ANÁLISIS COMPLETADO'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'📊 Resumen:')
        self.stdout.write(f'  - Total de reseñas analizadas: {total_reviews}')
        self.stdout.write(f'  - Reseñas actualizadas: {updated_count}')
        
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'  - Errores encontrados: {error_count}'))
        
        self.stdout.write(f'\n📈 Distribución de sentimientos:')
        self.stdout.write(f'  - Positivas: {sentiments_counter["POSITIVO"]} '
                         f'({sentiments_counter["POSITIVO"]/max(updated_count, 1)*100:.1f}%)')
        self.stdout.write(f'  - Neutras: {sentiments_counter["NEUTRO"]} '
                         f'({sentiments_counter["NEUTRO"]/max(updated_count, 1)*100:.1f}%)')
        self.stdout.write(f'  - Negativas: {sentiments_counter["NEGATIVO"]} '
                         f'({sentiments_counter["NEGATIVO"]/max(updated_count, 1)*100:.1f}%)')
        self.stdout.write('=' * 70)
