from django.core.management.base import BaseCommand
from django.utils import timezone
from offers.services import OfferService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Notifica ofertas que están por expirar (menos de 24 horas)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Horas antes de la expiración para notificar (default: 24)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin enviar notificaciones reales'
        )

    def handle(self, *args, **options):
        hours_threshold = options['hours']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS(f'🔍 Buscando ofertas que expiran en menos de {hours_threshold} horas...')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 MODO DRY-RUN: No se enviarán notificaciones reales')
            )

        try:
            # Llamar al método de OfferService
            expiring_offers = OfferService.check_expiring_offers()

            if expiring_offers:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Se notificaron {len(expiring_offers)} ofertas por expirar')
                )
                for offer in expiring_offers:
                    self.stdout.write(f'  - {offer.name} (expira: {offer.end_date})')
            else:
                self.stdout.write(
                    self.style.SUCCESS('ℹ️ No hay ofertas por expirar en este momento')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error ejecutando comando: {str(e)}')
            )
            logger.error(f'Error en check_expiring_offers: {str(e)}', exc_info=True)
            return

        self.stdout.write(
            self.style.SUCCESS('🎉 Comando completado exitosamente')
        )