import os
import django
import random
from datetime import datetime, timedelta
import pytz

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsales_backend.settings')
django.setup()

from orders.models import Order
from django.utils import timezone

# Rango de fechas: 3 años (2023-01-01 a 2025-10-27)
START_DATE = datetime(2023, 1, 1, tzinfo=pytz.UTC)
END_DATE = datetime(2025, 10, 27, tzinfo=pytz.UTC)

print("🔧 Actualizando fechas de órdenes...")
print(f"📅 Rango: {START_DATE.date()} a {END_DATE.date()}\n")

# Obtener todas las órdenes
orders = Order.objects.all().order_by('id')
total_orders = orders.count()

print(f"📊 Total de órdenes a actualizar: {total_orders}")

# Distribuir fechas de manera uniforme en el rango
days_range = (END_DATE - START_DATE).days
updated = 0

for i, order in enumerate(orders, 1):
    # Generar fecha aleatoria dentro del rango
    random_days = random.randint(0, days_range)
    random_hours = random.randint(0, 23)
    random_minutes = random.randint(0, 59)
    random_seconds = random.randint(0, 59)
    
    new_date = START_DATE + timedelta(
        days=random_days,
        hours=random_hours,
        minutes=random_minutes,
        seconds=random_seconds
    )
    
    # Actualizar la fecha (bypass auto_now_add usando update)
    Order.objects.filter(id=order.id).update(created_at=new_date)
    updated += 1
    
    if updated % 200 == 0:
        print(f"  ✅ Actualizadas {updated}/{total_orders} órdenes...")

print(f"\n✅ Total actualizado: {updated} órdenes")

# Verificar el rango final
first_order = Order.objects.earliest('created_at')
last_order = Order.objects.latest('created_at')

print(f"\n📊 Verificación:")
print(f"  • Primera orden: {first_order.created_at}")
print(f"  • Última orden: {last_order.created_at}")
print(f"  • Total órdenes: {Order.objects.count()}")

print("\n✅ Proceso completado!")
