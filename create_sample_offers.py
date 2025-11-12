"""
Script para crear ofertas de prueba en la base de datos
"""
import os
import django
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsales_backend.settings')
django.setup()

from offers.models import Offer
from products.models import Product

def create_sample_offers():
    """Crea ofertas de ejemplo para demostración"""
    
    print("\n🏗️  Creando ofertas de prueba...\n")
    
    # Verificar si ya hay ofertas
    existing_offers = Offer.objects.count()
    if existing_offers > 0:
        print(f"⚠️  Ya existen {existing_offers} ofertas en la base de datos")
        response = input("¿Deseas eliminar las ofertas existentes y crear nuevas? (s/n): ")
        if response.lower() == 's':
            Offer.objects.all().delete()
            print("✅ Ofertas existentes eliminadas")
        else:
            print("❌ Operación cancelada")
            return
    
    # Obtener algunos productos para asociar a las ofertas
    products = list(Product.objects.all()[:10])
    
    if not products:
        print("❌ No hay productos en la base de datos. Crea productos primero.")
        return
    
    print(f"📦 Productos disponibles: {len(products)}")
    
    # Fechas para las ofertas
    now = datetime.now()
    
    # Oferta 1: Venta Flash (activa)
    offer1 = Offer.objects.create(
        name="🔥 Venta Flash - 50% OFF",
        description="¡Aprovecha nuestra venta flash! 50% de descuento en productos seleccionados. Oferta válida por tiempo limitado.",
        offer_type="FLASH_SALE",
        discount_percentage=Decimal('50.00'),
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=2),
        status="ACTIVE",
        priority=10,  # Alta prioridad (será featured)
        min_purchase_amount=Decimal('50.00'),
        max_uses=100,
        max_uses_per_user=1,
        views_count=245,
        clicks_count=67,
        conversions_count=12
    )
    offer1.applicable_products.set(products[:3])
    print(f"✅ Creada: {offer1.name}")
    
    # Oferta 2: Oferta del Día (activa)
    offer2 = Offer.objects.create(
        name="⭐ Oferta del Día - 30% OFF",
        description="Oferta especial del día en productos premium. No te pierdas esta oportunidad única.",
        offer_type="DAILY_DEAL",
        discount_percentage=Decimal('30.00'),
        start_date=now - timedelta(hours=2),
        end_date=now + timedelta(hours=22),
        status="ACTIVE",
        priority=8,  # Featured
        min_purchase_amount=Decimal('30.00'),
        max_uses=50,
        max_uses_per_user=1,
        views_count=189,
        clicks_count=43,
        conversions_count=8
    )
    offer2.applicable_products.set(products[3:6])
    print(f"✅ Creada: {offer2.name}")
    
    # Oferta 3: Temporada (activa)
    offer3 = Offer.objects.create(
        name="🎄 Oferta de Temporada - 25% OFF",
        description="Celebra con nosotros esta temporada especial. 25% de descuento en toda la tienda.",
        offer_type="SEASONAL",
        discount_percentage=Decimal('25.00'),
        start_date=now - timedelta(days=5),
        end_date=now + timedelta(days=25),
        status="ACTIVE",
        priority=6,  # Featured
        min_purchase_amount=Decimal('40.00'),
        max_uses=200,
        max_uses_per_user=2,
        views_count=532,
        clicks_count=124,
        conversions_count=28
    )
    offer3.applicable_products.set(products[::2])  # Productos alternados
    print(f"✅ Creada: {offer3.name}")
    
    # Oferta 4: Liquidación (activa)
    offer4 = Offer.objects.create(
        name="🏷️ Liquidación - 40% OFF",
        description="Últimas unidades en liquidación. Descuentos de hasta 40% en productos seleccionados.",
        offer_type="CLEARANCE",
        discount_percentage=Decimal('40.00'),
        start_date=now - timedelta(days=10),
        end_date=now + timedelta(days=5),
        status="ACTIVE",
        priority=5,  # Featured
        min_purchase_amount=Decimal('20.00'),
        max_uses=150,
        max_uses_per_user=3,
        views_count=423,
        clicks_count=98,
        conversions_count=19
    )
    offer4.applicable_products.set(products[6:9])
    print(f"✅ Creada: {offer4.name}")
    
    # Oferta 5: Oferta normal (activa, no featured)
    offer5 = Offer.objects.create(
        name="💼 Descuento Especial - 15% OFF",
        description="Descuento especial para nuevos clientes. 15% en tu primera compra.",
        offer_type="DAILY_DEAL",
        discount_percentage=Decimal('15.00'),
        start_date=now,
        end_date=now + timedelta(days=30),
        status="ACTIVE",
        priority=3,  # No featured (< 5)
        min_purchase_amount=Decimal('10.00'),
        max_uses=1000,
        max_uses_per_user=1,
        views_count=156,
        clicks_count=34,
        conversions_count=7
    )
    offer5.applicable_products.set(products[1:4])
    print(f"✅ Creada: {offer5.name}")
    
    # Oferta 6: Pausada (para testing)
    offer6 = Offer.objects.create(
        name="🛑 Oferta Pausada - 20% OFF",
        description="Esta oferta está temporalmente pausada.",
        offer_type="FLASH_SALE",
        discount_percentage=Decimal('20.00'),
        start_date=now - timedelta(days=2),
        end_date=now + timedelta(days=3),
        status="PAUSED",
        priority=4,
        min_purchase_amount=Decimal('25.00'),
        max_uses=75,
        max_uses_per_user=1
    )
    offer6.applicable_products.set(products[4:7])
    print(f"✅ Creada: {offer6.name} (PAUSADA)")
    
    # Oferta 7: Expirada (para testing)
    offer7 = Offer.objects.create(
        name="⏱️ Oferta Expirada - 35% OFF",
        description="Esta oferta ya ha expirado.",
        offer_type="SEASONAL",
        discount_percentage=Decimal('35.00'),
        start_date=now - timedelta(days=20),
        end_date=now - timedelta(days=1),
        status="EXPIRED",
        priority=7,
        min_purchase_amount=Decimal('30.00'),
        max_uses=50,
        max_uses_per_user=1,
        views_count=687,
        clicks_count=145,
        conversions_count=31
    )
    offer7.applicable_products.set(products[2:5])
    print(f"✅ Creada: {offer7.name} (EXPIRADA)")
    
    print("\n" + "="*60)
    print(f"✅ OFERTAS CREADAS EXITOSAMENTE")
    print("="*60)
    
    # Resumen
    total_offers = Offer.objects.count()
    active_offers = Offer.objects.filter(status='ACTIVE').count()
    featured_offers = Offer.objects.filter(status='ACTIVE', priority__gte=5).count()
    
    print(f"\n📊 RESUMEN:")
    print(f"  Total de ofertas: {total_offers}")
    print(f"  Ofertas activas: {active_offers}")
    print(f"  Ofertas destacadas: {featured_offers}")
    print(f"  Ofertas pausadas: {Offer.objects.filter(status='PAUSED').count()}")
    print(f"  Ofertas expiradas: {Offer.objects.filter(status='EXPIRED').count()}")
    
    print("\n🧪 PRUEBA LOS ENDPOINTS:")
    print("  - GET /api/offers/offers/ → Todas las ofertas activas")
    print("  - GET /api/offers/offers/active/ → Ofertas activas")
    print("  - GET /api/offers/offers/featured/ → Ofertas destacadas (priority >= 5)")
    print("  - GET /api/offers/categories/ → Categorías de ofertas")
    
    print("\n✅ Todo listo para probar las funcionalidades!")


if __name__ == "__main__":
    create_sample_offers()
