import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsales_backend.settings')
django.setup()

from orders.models import Order

# Ver estados de pago disponibles
estados = Order.objects.values_list('payment_status', flat=True).distinct()
print("Estados de pago existentes:", list(estados))

# Contar órdenes por estado
for estado in estados:
    count = Order.objects.filter(payment_status=estado).count()
    print(f"  - {estado}: {count} órdenes")
