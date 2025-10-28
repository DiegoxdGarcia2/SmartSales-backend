import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsales_backend.settings')
django.setup()

from orders.models import Order
from django.db.models import Min, Max

stats = Order.objects.aggregate(
    min_date=Min('created_at'),
    max_date=Max('created_at')
)

print(f'Total órdenes: {Order.objects.count()}')
print(f'Fecha mínima: {stats["min_date"]}')
print(f'Fecha máxima: {stats["max_date"]}')
