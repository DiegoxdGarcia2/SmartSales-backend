"""
Script para verificar el problema con NotificationPreference
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsales_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.models import NotificationPreference
from notifications.serializers import NotificationPreferenceSerializer

User = get_user_model()

try:
    # Obtener usuario admin
    admin = User.objects.get(username='admin')
    print(f"✅ Usuario encontrado: {admin.username}")
    
    # Intentar obtener o crear preferencias
    prefs, created = NotificationPreference.objects.get_or_create(user=admin)
    print(f"\n{'✅ Preferencias CREADAS' if created else '✅ Preferencias YA EXISTÍAN'}")
    
    # Serializar
    serializer = NotificationPreferenceSerializer(prefs)
    print(f"\n📊 Datos serializados:")
    print(f"  - offers_push: {serializer.data.get('offers_push')}")
    print(f"  - offers_email: {serializer.data.get('offers_email')}")
    print(f"  - orders_push: {serializer.data.get('orders_push')}")
    
    print(f"\n✅ TODO FUNCIONA CORRECTAMENTE")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
