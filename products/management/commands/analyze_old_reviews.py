from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from products.models import Review
from products.gemini_sentiment import analyze_review_sentiment_advanced, extract_basic_sentiment
import logging
import time

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Analiza reseñas antiguas con Gemini AI que no tienen análisis previo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecuta en modo simulación sin modificar la base de datos',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Número de reseñas a procesar por lote (default: 10)',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Segundos de espera entre análisis para evitar rate limits (default: 1.0)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        delay = options['delay']

        self.stdout.write(
            self.style.WARNING(
                f"🔍 ANALIZANDO RESEÑAS ANTIGUAS CON GEMINI AI\n"
                f"Modo: {'SIMULACIÓN (dry-run)' if dry_run else 'PRODUCCIÓN'}\n"
                f"Lote: {batch_size} reseñas\n"
                f"Delay: {delay}s entre análisis\n"
            )
        )

        # Buscar reseñas sin análisis de Gemini
        reviews_to_analyze = Review.objects.filter(
            sentiment_confidence__isnull=True
        ).select_related('product', 'user').order_by('created_at')

        total_reviews = reviews_to_analyze.count()

        if total_reviews == 0:
            self.stdout.write(
                self.style.SUCCESS("✅ No hay reseñas pendientes de análisis.")
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"📊 Encontradas {total_reviews} reseñas sin análisis de Gemini"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 MODO SIMULACIÓN - No se modificarán datos")
            )

        # Procesar en lotes
        processed = 0
        successful = 0
        failed = 0

        for i in range(0, total_reviews, batch_size):
            batch = reviews_to_analyze[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_reviews + batch_size - 1) // batch_size

            self.stdout.write(
                self.style.WARNING(
                    f"\n📦 Procesando lote {batch_num}/{total_batches} "
                    f"({len(batch)} reseñas)"
                )
            )

            for review in batch:
                processed += 1

                self.stdout.write(
                    f"  🔍 [{processed}/{total_reviews}] "
                    f"Review ID {review.id} - {review.product.name[:30]}... "
                    f"(Rating: {review.rating}/5)"
                )

                try:
                    # Aplicar análisis de Gemini (misma lógica que para reseñas nuevas)
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

                    if not dry_run:
                        # Actualizar la reseña en una transacción segura
                        with transaction.atomic():
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

                    successful += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"    ✅ {'SIMULADO' if dry_run else 'ANALIZADO'}: "
                            f"{sentiment} ({sentiment_confidence:.1%}) - {sentiment_summary[:50]}..."
                        )
                    )

                except Exception as e:
                    failed += 1
                    logger.error(
                        f"❌ Error analizando review {review.id}: {str(e)}",
                        exc_info=True
                    )
                    self.stdout.write(
                        self.style.ERROR(
                            f"    ❌ ERROR: {str(e)[:100]}..."
                        )
                    )

                # Pequeña pausa para evitar rate limits de Gemini
                if delay > 0 and processed < total_reviews:
                    time.sleep(delay)

        # Resumen final
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 ANÁLISIS COMPLETADO\n"
                f"📊 Total procesado: {processed}\n"
                f"✅ Exitosos: {successful}\n"
                f"❌ Fallidos: {failed}\n"
                f"📈 Tasa de éxito: {(successful/total_reviews*100):.1f}%" if total_reviews > 0 else "N/A"
            )
        )

        if failed > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  {failed} reseñas fallaron. Revisa los logs para detalles."
                )
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "🔄 Ejecuta sin --dry-run para aplicar los cambios realmente."
                )
            )