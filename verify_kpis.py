"""
Script para verificar KPIs directamente desde la base de datos.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsales_backend.settings')
django.setup()

from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, Sum, Count
from orders.models import Order, OrderItem
from users.models import User

print("=" * 80)
print("📊 CALCULANDO KPIs DIRECTAMENTE")
print("=" * 80)

# 1. Total Clientes
total_customers = User.objects.filter(role__name='CLIENTE').count()
print(f"\n👥 Total Clientes (rol CLIENTE): {total_customers:,}")

# 2. Órdenes Pagadas
orders_pagadas = Order.objects.filter(status='PAGADO')
total_orders_paid = orders_pagadas.count()
print(f"📦 Total Órdenes Pagadas: {total_orders_paid:,}")

# 3. Ticket Promedio
average_order_value = orders_pagadas.aggregate(avg_total=Avg('total_price'))['avg_total'] or 0
print(f"💵 Ticket Promedio: ${float(average_order_value):,.2f}")

# 4. Ingresos Totales
total_revenue = orders_pagadas.aggregate(total_sum=Sum('total_price'))['total_sum'] or 0
print(f"💰 Ingresos Totales: ${float(total_revenue):,.2f}")

# 5. Órdenes últimos 30 días
thirty_days_ago = timezone.now() - timedelta(days=30)
recent_orders_count = orders_pagadas.filter(created_at__gte=thirty_days_ago).count()
print(f"📅 Órdenes (últimos 30 días): {recent_orders_count:,}")

# 6. Top 3 Productos Más Vendidos
print("\n🏆 Top 3 Productos Más Vendidos:")
top_products = OrderItem.objects.filter(
    order__status='PAGADO'
).values(
    'product__name'
).annotate(
    total_sold=Sum('quantity')
).order_by('-total_sold')[:3]

for i, item in enumerate(top_products, 1):
    print(f"  {i}. {item['product__name']}: {item['total_sold']:,} unidades")

print("\n" + "=" * 80)
print("✅ KPIs calculados exitosamente")
print("=" * 80)
