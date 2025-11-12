"""
Comando de Django para crear ofertas de prueba
"""
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from decimal import Decimal
from offers.models import Offer
from products.models import Product


class Command(BaseCommand):
    help = 'Crea ofertas de prueba en la base de datos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Elimina todas las ofertas existentes antes de crear nuevas',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("\n🏗️  Creando ofertas de prueba...\n"))
        
        # Reset si se especifica
        if options['reset']:
            count = Offer.objects.count()
            if count > 0:
                Offer.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f"✅ {count} ofertas eliminadas"))
        
        # Verificar si ya hay ofertas
        existing_offers = Offer.objects.count()
        if existing_offers > 0:
            self.stdout.write(self.style.WARNING(f"⚠️  Ya existen {existing_offers} ofertas. Usa --reset para eliminarlas."))
            return
        
        # Obtener productos
        products = list(Product.objects.all()[:10])
        
        if not products:
            self.stdout.write(self.style.ERROR("❌ No hay productos en la base de datos."))
            return
        
        self.stdout.write(f"📦 Productos disponibles: {len(products)}")
        
        now = datetime.now()
        
        offers_data = [
            {
                'name': "🔥 Venta Flash - 50% OFF",
                'description': "¡Aprovecha nuestra venta flash! 50% de descuento en productos seleccionados.",
                'offer_type': "FLASH_SALE",
                'discount_percentage': Decimal('50.00'),
                'start_date': now - timedelta(days=1),
                'end_date': now + timedelta(days=2),
                'status': "ACTIVE",
                'priority': 10,
                'min_purchase_amount': Decimal('50.00'),
                'max_uses': 100,
                'max_uses_per_user': 1,
                'views_count': 245,
                'clicks_count': 67,
                'conversions_count': 12,
                'products': products[:3]
            },
            {
                'name': "⭐ Oferta del Día - 30% OFF",
                'description': "Oferta especial del día en productos premium.",
                'offer_type': "DAILY_DEAL",
                'discount_percentage': Decimal('30.00'),
                'start_date': now - timedelta(hours=2),
                'end_date': now + timedelta(hours=22),
                'status': "ACTIVE",
                'priority': 8,
                'min_purchase_amount': Decimal('30.00'),
                'max_uses': 50,
                'max_uses_per_user': 1,
                'views_count': 189,
                'clicks_count': 43,
                'conversions_count': 8,
                'products': products[3:6]
            },
            {
                'name': "🎄 Oferta de Temporada - 25% OFF",
                'description': "Celebra con nosotros esta temporada especial.",
                'offer_type': "SEASONAL",
                'discount_percentage': Decimal('25.00'),
                'start_date': now - timedelta(days=5),
                'end_date': now + timedelta(days=25),
                'status': "ACTIVE",
                'priority': 6,
                'min_purchase_amount': Decimal('40.00'),
                'max_uses': 200,
                'max_uses_per_user': 2,
                'views_count': 532,
                'clicks_count': 124,
                'conversions_count': 28,
                'products': products[::2]
            },
            {
                'name': "🏷️ Liquidación - 40% OFF",
                'description': "Últimas unidades en liquidación.",
                'offer_type': "CLEARANCE",
                'discount_percentage': Decimal('40.00'),
                'start_date': now - timedelta(days=10),
                'end_date': now + timedelta(days=5),
                'status': "ACTIVE",
                'priority': 5,
                'min_purchase_amount': Decimal('20.00'),
                'max_uses': 150,
                'max_uses_per_user': 3,
                'views_count': 423,
                'clicks_count': 98,
                'conversions_count': 19,
                'products': products[6:9]
            },
            {
                'name': "💼 Descuento Especial - 15% OFF",
                'description': "Descuento especial para nuevos clientes.",
                'offer_type': "DAILY_DEAL",
                'discount_percentage': Decimal('15.00'),
                'start_date': now,
                'end_date': now + timedelta(days=30),
                'status': "ACTIVE",
                'priority': 3,
                'min_purchase_amount': Decimal('10.00'),
                'max_uses': 1000,
                'max_uses_per_user': 1,
                'views_count': 156,
                'clicks_count': 34,
                'conversions_count': 7,
                'products': products[1:4]
            }
        ]
        
        for offer_data in offers_data:
            products_to_add = offer_data.pop('products')
            offer = Offer.objects.create(**offer_data)
            offer.applicable_products.set(products_to_add)
            self.stdout.write(self.style.SUCCESS(f"✅ Creada: {offer.name}"))
        
        # Resumen
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("✅ OFERTAS CREADAS EXITOSAMENTE"))
        self.stdout.write("="*60)
        
        total_offers = Offer.objects.count()
        active_offers = Offer.objects.filter(status='ACTIVE').count()
        featured_offers = Offer.objects.filter(status='ACTIVE', priority__gte=5).count()
        
        self.stdout.write(f"\n📊 RESUMEN:")
        self.stdout.write(f"  Total de ofertas: {total_offers}")
        self.stdout.write(f"  Ofertas activas: {active_offers}")
        self.stdout.write(f"  Ofertas destacadas: {featured_offers}")
        
        self.stdout.write("\n✅ Todo listo para probar las funcionalidades!")
