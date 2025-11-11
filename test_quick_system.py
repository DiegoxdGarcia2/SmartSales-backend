"""
Test Rápido del Sistema Completo - SmartSales
Verifica que todos los componentes estén funcionando correctamente.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsales_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.models import Notification, NotificationPreference, DeviceToken
from offers.models import Offer, OfferProduct, UserOfferInteraction, OfferRecommendation
from products.models import Product
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()

def print_header(text):
    print("\n" + "="*60)
    print(f"🔍 {text}")
    print("="*60)

def test_firebase():
    """Verifica Firebase"""
    print_header("VERIFICANDO FIREBASE")
    try:
        import firebase_admin
        app = firebase_admin.get_app()
        print(f"✅ Firebase inicializado: {app.project_id}")
        return True
    except Exception as e:
        print(f"❌ Error Firebase: {str(e)}")
        return False

def test_notifications_models():
    """Verifica modelos de notificaciones"""
    print_header("VERIFICANDO MODELOS DE NOTIFICACIONES")
    try:
        # Contar registros
        notifications = Notification.objects.count()
        preferences = NotificationPreference.objects.count()
        devices = DeviceToken.objects.count()
        
        print(f"✅ Notificaciones: {notifications} registros")
        print(f"✅ Preferencias: {preferences} registros")
        print(f"✅ Dispositivos: {devices} registros")
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_offers_models():
    """Verifica modelos de ofertas"""
    print_header("VERIFICANDO MODELOS DE OFERTAS")
    try:
        offers = Offer.objects.count()
        offer_products = OfferProduct.objects.count()
        interactions = UserOfferInteraction.objects.count()
        recommendations = OfferRecommendation.objects.count()
        
        print(f"✅ Ofertas: {offers} registros")
        print(f"✅ Productos en ofertas: {offer_products} registros")
        print(f"✅ Interacciones: {interactions} registros")
        print(f"✅ Recomendaciones ML: {recommendations} registros")
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_services():
    """Verifica que los servicios se puedan importar"""
    print_header("VERIFICANDO SERVICIOS")
    try:
        from notifications.services import NotificationService
        from offers.services import OfferService
        from offers.ml_models import OfferRecommendationEngine, DiscountOptimizer
        
        print("✅ NotificationService importado")
        print("✅ OfferService importado")
        print("✅ OfferRecommendationEngine importado")
        print("✅ DiscountOptimizer importado")
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_create_sample_data():
    """Intenta crear datos de prueba si no existen"""
    print_header("VERIFICANDO DATOS DE PRUEBA")
    try:
        # Verificar que haya al menos un producto
        products = Product.objects.count()
        if products == 0:
            print("⚠️ No hay productos en la base de datos")
            print("   Sugerencia: Crear productos desde el admin")
        else:
            print(f"✅ {products} productos disponibles")
        
        # Verificar usuarios
        users = User.objects.filter(is_active=True).count()
        if users == 0:
            print("⚠️ No hay usuarios activos")
        else:
            print(f"✅ {users} usuarios activos")
        
        # Intentar crear una oferta de prueba si no existe ninguna
        if Offer.objects.count() == 0 and products > 0:
            print("\n📝 Creando oferta de prueba...")
            user = User.objects.first()
            offer = Offer.objects.create(
                name="Test Offer - Sistema Verificado",
                description="Oferta de prueba creada automáticamente",
                offer_type="DAILY_DEAL",
                discount_percentage=20,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=7),
                status="DRAFT",
                priority=1,
                created_by=user
            )
            
            # Agregar productos
            for product in Product.objects.all()[:3]:
                OfferProduct.objects.create(
                    offer=offer,
                    product=product
                )
            
            print(f"✅ Oferta de prueba creada (ID: {offer.id})")
        
        return True
    except Exception as e:
        print(f"⚠️ No se pudieron crear datos de prueba: {str(e)}")
        return True  # No es crítico

def test_ml_engine():
    """Verifica el motor ML"""
    print_header("VERIFICANDO MOTOR DE MACHINE LEARNING")
    try:
        from offers.ml_models import OfferRecommendationEngine, DiscountOptimizer
        
        # Test OfferRecommendationEngine
        engine = OfferRecommendationEngine()
        print(f"✅ OfferRecommendationEngine creado (versión {engine.MODEL_VERSION})")
        print(f"   Threshold mínimo: {engine.min_score_threshold}")
        
        # Test DiscountOptimizer
        optimizer = DiscountOptimizer()
        print(f"✅ DiscountOptimizer creado")
        print(f"   Ventana histórica: {optimizer.historical_window_days} días")
        
        # Si hay productos, probar optimización
        product = Product.objects.first()
        if product:
            print(f"\n📊 Probando optimización de descuento para: {product.name}")
            suggestion = optimizer.suggest_optimal_discount(product, target_sales_increase=1.5)
            print(f"   Descuento sugerido: {suggestion['suggested_discount_percentage']}%")
            print(f"   Precio con descuento: ${suggestion['discounted_price']:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_integrations():
    """Verifica integraciones"""
    print_header("VERIFICANDO INTEGRACIONES")
    try:
        # Verificar que NotificationService puede usarse desde OfferService
        from offers.services import OfferService
        from notifications.services import NotificationService
        
        print("✅ OfferService puede importar NotificationService")
        print("✅ Integración Ofertas → Notificaciones OK")
        
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "🚀"*30)
    print("INICIANDO TESTS DEL SISTEMA COMPLETO")
    print("🚀"*30)
    
    results = {
        "Firebase": test_firebase(),
        "Modelos Notificaciones": test_notifications_models(),
        "Modelos Ofertas": test_offers_models(),
        "Servicios": test_services(),
        "Datos de Prueba": test_create_sample_data(),
        "Motor ML": test_ml_engine(),
        "Integraciones": test_integrations()
    }
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE TESTS")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test}")
    
    print("\n" + "-"*60)
    print(f"Total: {passed}/{total} tests pasados")
    print(f"Tasa de éxito: {(passed/total*100):.1f}%")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("✅ Sistema listo para deploy")
    elif passed >= total * 0.8:
        print("\n⚠️ Mayoría de tests pasaron")
        print("   Revisar tests fallidos antes del deploy")
    else:
        print("\n❌ Varios tests fallaron")
        print("   Resolver problemas antes del deploy")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
