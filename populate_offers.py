"""
Script Python para poblar ofertas usando Django ORM directamente
Se ejecuta en producción a través de Django shell
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsales_backend.settings')

import django
django.setup()

from datetime import datetime, timedelta
from decimal import Decimal
from offers.models import Offer
from products.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()

# Limpiar ofertas existentes
print("\n🧹 Limpiando ofertas existentes...")
count = Offer.objects.count()
if count > 0:
    Offer.objects.all().delete()
    print(f"✅ {count} ofertas eliminadas")

# Obtener productos
products = list(Product.objects.all()[:10])
if not products:
    print("❌ No hay productos en la base de datos")
    exit(1)

print(f"\n📦 Productos disponibles: {len(products)}")

# Obtener usuario admin (created_by)
try:
    admin_user = User.objects.get(username='admin')
except User.DoesNotExist:
    admin_user = User.objects.filter(is_staff=True).first()

now = datetime.now()

print("\n🏗️  Creando ofertas...")

# Oferta 1: Venta Flash 50%
offer1 = Offer.objects.create(
    name="🔥 Venta Flash - 50% OFF",
    description="¡Aprovecha nuestra venta flash! 50% de descuento en productos seleccionados.",
    offer_type="FLASH_SALE",
    discount_percentage=Decimal('50.00'),
    start_date=now - timedelta(days=1),
    end_date=now + timedelta(days=2),
    status="ACTIVE",
    priority=10,
    terms_conditions="Válido solo para productos seleccionados.",
    min_purchase_amount=Decimal('50.00'),
    max_discount_amount=Decimal('500.00'),
    max_uses=100,
    max_uses_per_user=1,
    views_count=245,
    clicks_count=67,
    conversions_count=12,
    revenue_generated=Decimal('1250.50'),
    created_by=admin_user
)
offer1.applicable_products.set(products[:3])
print(f"✅ {offer1.name}")

# Oferta 2: Oferta del Día 30%
offer2 = Offer.objects.create(
    name="⭐ Oferta del Día - 30% OFF",
    description="Oferta especial del día en productos premium.",
    offer_type="DAILY_DEAL",
    discount_percentage=Decimal('30.00'),
    start_date=now - timedelta(hours=2),
    end_date=now + timedelta(hours=22),
    status="ACTIVE",
    priority=8,
    terms_conditions="Válido por 24 horas.",
    min_purchase_amount=Decimal('30.00'),
    max_discount_amount=Decimal('300.00'),
    max_uses=50,
    max_uses_per_user=1,
    views_count=189,
    clicks_count=43,
    conversions_count=8,
    revenue_generated=Decimal('567.80'),
    created_by=admin_user
)
offer2.applicable_products.set(products[3:6])
print(f"✅ {offer2.name}")

# Oferta 3: Temporada 25%
offer3 = Offer.objects.create(
    name="🎄 Oferta de Temporada - 25% OFF",
    description="Celebra con nosotros esta temporada especial.",
    offer_type="SEASONAL",
    discount_percentage=Decimal('25.00'),
    start_date=now - timedelta(days=5),
    end_date=now + timedelta(days=25),
    status="ACTIVE",
    priority=6,
    terms_conditions="Válido durante toda la temporada.",
    min_purchase_amount=Decimal('40.00'),
    max_discount_amount=Decimal('400.00'),
    max_uses=200,
    max_uses_per_user=2,
    views_count=532,
    clicks_count=124,
    conversions_count=28,
    revenue_generated=Decimal('2145.75'),
    created_by=admin_user
)
offer3.applicable_products.set(products[::2][:5])
print(f"✅ {offer3.name}")

# Oferta 4: Liquidación 40%
offer4 = Offer.objects.create(
    name="🏷️ Liquidación - 40% OFF",
    description="Últimas unidades en liquidación.",
    offer_type="CLEARANCE",
    discount_percentage=Decimal('40.00'),
    start_date=now - timedelta(days=10),
    end_date=now + timedelta(days=5),
    status="ACTIVE",
    priority=5,
    terms_conditions="Hasta agotar stock.",
    min_purchase_amount=Decimal('20.00'),
    max_discount_amount=Decimal('200.00'),
    max_uses=150,
    max_uses_per_user=3,
    views_count=423,
    clicks_count=98,
    conversions_count=19,
    revenue_generated=Decimal('987.30'),
    created_by=admin_user
)
offer4.applicable_products.set(products[6:9] if len(products) > 6 else products[:3])
print(f"✅ {offer4.name}")

# Oferta 5: Descuento 15%
offer5 = Offer.objects.create(
    name="💼 Descuento Especial - 15% OFF",
    description="Descuento especial para nuevos clientes.",
    offer_type="DAILY_DEAL",
    discount_percentage=Decimal('15.00'),
    start_date=now,
    end_date=now + timedelta(days=30),
    status="ACTIVE",
    priority=3,
    terms_conditions="Válido solo para nuevos clientes.",
    min_purchase_amount=Decimal('10.00'),
    max_discount_amount=Decimal('100.00'),
    max_uses=1000,
    max_uses_per_user=1,
    views_count=156,
    clicks_count=34,
    conversions_count=7,
    revenue_generated=Decimal('345.60'),
    created_by=admin_user
)
offer5.applicable_products.set(products[1:4])
print(f"✅ {offer5.name}")

# Resumen
print("\n" + "="*60)
print("✅ OFERTAS CREADAS EXITOSAMENTE")
print("="*60)

total_offers = Offer.objects.count()
active_offers = Offer.objects.filter(status='ACTIVE').count()
featured_offers = Offer.objects.filter(status='ACTIVE', priority__gte=5).count()

print(f"\n📊 RESUMEN:")
print(f"  Total de ofertas: {total_offers}")
print(f"  Ofertas activas: {active_offers}")
print(f"  Ofertas destacadas: {featured_offers}")
print("\n✅ Todo listo para probar!")
