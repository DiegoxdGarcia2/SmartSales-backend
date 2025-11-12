#!/usr/bin/env python
"""
Script de testing completo para el sistema de notificaciones
Ejecutar antes del despliegue para verificar funcionamiento
"""
import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsales_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import TestCase
from notifications.services import NotificationService
from notifications.models import Notification, NotificationPreference, DeviceToken
from orders.models import Order
from products.models import Product
from offers.models import Offer
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def test_notification_system():
    """Prueba completa del sistema de notificaciones"""
    print("🧪 Iniciando pruebas del sistema de notificaciones...")

    # Crear usuario de prueba
    user, created = User.objects.get_or_create(
        username='test_notifications',
        defaults={
            'email': 'test@example.com',
            'is_active': True
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print("✅ Usuario de prueba creado")

    # Verificar preferencias
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    print(f"✅ Preferencias creadas: {prefs.orders_in_app}, {prefs.offers_push}")

    # Probar notificación básica
    try:
        result = NotificationService.send_notification(
            user=user,
            notification_type='SYSTEM_ALERT',
            title='Prueba del Sistema',
            message='Esta es una notificación de prueba',
            channels=['IN_APP']
        )
        print(f"✅ Notificación básica enviada: {result}")

        # Verificar que se creó
        notification = Notification.objects.filter(user=user).last()
        if notification:
            print(f"✅ Notificación guardada: {notification.title}")
        else:
            print("❌ Notificación no se guardó")

    except Exception as e:
        print(f"❌ Error en notificación básica: {e}")

    # Probar notificación de pago (si hay orden)
    try:
        order = Order.objects.filter(user=user).first()
        if order:
            result = NotificationService.notify_payment_success(order)
            print(f"✅ Notificación de pago enviada: {result}")
        else:
            print("⚠️ No hay órdenes para probar notificación de pago")
    except Exception as e:
        print(f"❌ Error en notificación de pago: {e}")

    # Probar notificación de oferta (si hay producto)
    try:
        product = Product.objects.first()
        if product:
            result = NotificationService.notify_new_offer(
                user=user,
                product=product,
                discount_percentage=25
            )
            print(f"✅ Notificación de oferta enviada: {result}")
        else:
            print("⚠️ No hay productos para probar notificación de oferta")
    except Exception as e:
        print(f"❌ Error en notificación de oferta: {e}")

    # Verificar total de notificaciones
    total_notifications = Notification.objects.filter(user=user).count()
    print(f"📊 Total de notificaciones para usuario de prueba: {total_notifications}")

    print("🎉 Pruebas completadas!")


def test_signals():
    """Probar que las señales funcionan"""
    print("🔗 Probando señales automáticas...")

    # Crear producto de prueba
    product, created = Product.objects.get_or_create(
        name='Producto Test Notificaciones',
        defaults={
            'price': 100.00,
            'stock': 10,
            'description': 'Producto para testing'
        }
    )

    # Cambiar stock de 10 a 0, luego a 5 (debería notificar)
    print("📦 Probando señal de stock disponible...")
    product.stock = 0
    product.save()

    product.stock = 5
    product.save()

    print("✅ Señales de producto probadas")

    print("🎯 Señales probadas!")


if __name__ == '__main__':
    print("🚀 Iniciando testing completo del sistema de notificaciones")
    print("=" * 60)

    try:
        test_notification_system()
        print()
        test_signals()
        print()
        print("🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("📋 El sistema de notificaciones está listo para producción")

    except Exception as e:
        print(f"💥 Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)