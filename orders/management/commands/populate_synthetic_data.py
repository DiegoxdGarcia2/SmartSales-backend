"""
Comando de Django para poblar la base de datos con datos sintéticos.
Genera datos de ~3 años (Ene 2023 - Oct 2025) sin borrar datos existentes.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from faker import Faker
import random
from decimal import Decimal
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo

from users.models import ClientProfile, Role
from products.models import Category, Brand, Product, Review
from orders.models import Order, OrderItem

User = get_user_model()


class Command(BaseCommand):
    help = 'Genera datos sintéticos para ~3 años sin borrar datos existentes'

    def handle(self, *args, **options):
        fake = Faker('es_ES')
        
        # Configuración de cantidades
        NUM_CATEGORIES = 11
        NUM_BRANDS = 15
        NUM_PRODUCTS = 100
        NUM_CLIENTS = 120
        AVG_ORDERS_PER_CLIENT = 15
        MAX_ITEMS_PER_ORDER = 5
        REVIEW_CHANCE = 0.5
        
        # Rango de fechas
        START_DATE = datetime(2023, 1, 1, tzinfo=ZoneInfo("UTC"))
        END_DATE = datetime(2025, 10, 27, tzinfo=ZoneInfo("UTC"))
        
        self.stdout.write(self.style.SUCCESS('🚀 Iniciando generación de datos sintéticos...'))
        self.stdout.write(f'📅 Rango: {START_DATE.date()} a {END_DATE.date()}')
        
        try:
            with transaction.atomic():
                # Obtener rol de cliente
                role_cliente, _ = Role.objects.get_or_create(
                    name='CLIENTE',
                    defaults={'description': 'Cliente regular del sistema'}
                )
                
                # ==================== CATEGORÍAS ====================
                self.stdout.write('\n📁 Creando/Verificando Categorías...')
                category_names = [
                    'Refrigeración',  # Refrigeradores, Congeladores
                    'Lavado y Secado',  # Lavadoras, Secadoras, Lavavajillas
                    'Cocción',  # Hornos, Placas, Campanas
                    'Pequeños Electrodomésticos Cocina',  # Microondas, Cafeteras, Tostadoras
                    'Preparación de Alimentos',  # Batidoras, Freidoras, Robots de Cocina
                    'Limpieza del Hogar',  # Aspiradoras, Planchas
                    'Climatización',  # Ventiladores, Calefactores
                    'Cuidado Personal',  # Secadores, Afeitadoras, Cepillos eléctricos
                    'Televisores',  # Smart TV, LED, OLED
                    'Audio',  # Barras de sonido, Altavoces, Equipos
                    'Computación'  # Laptops, Tablets, Monitores
                ]
                
                category_ids = []
                for cat_name in category_names[:NUM_CATEGORIES]:
                    category, created = Category.objects.get_or_create(
                        name=cat_name,
                        defaults={'description': fake.sentence()}
                    )
                    category_ids.append(category.id)
                    if created:
                        self.stdout.write(f'  ✅ Creada: {cat_name}')
                    else:
                        self.stdout.write(f'  ℹ️  Existente: {cat_name}')
                
                # ==================== MARCAS ====================
                self.stdout.write('\n🏷️  Creando/Verificando Marcas...')
                brand_names = [
                    'Samsung', 'LG', 'Whirlpool', 'Electrolux',
                    'Bosch', 'Mabe', 'General Electric', 'Philips',
                    'Sony', 'Panasonic', 'Oster', 'Black+Decker',
                    'Midea', 'Teka', 'Indurama'
                ]
                
                brand_ids = []
                for brand_name in brand_names[:NUM_BRANDS]:
                    warranty_months = random.choice([6, 12, 18, 24])
                    brand, created = Brand.objects.get_or_create(
                        name=brand_name,
                        defaults={
                            'description': f'Productos de calidad {brand_name}',
                            'warranty_info': f'Garantía oficial de {warranty_months} meses',
                            'warranty_duration_months': warranty_months
                        }
                    )
                    brand_ids.append(brand.id)
                    if created:
                        self.stdout.write(f'  ✅ Creada: {brand_name} ({warranty_months} meses)')
                    else:
                        self.stdout.write(f'  ℹ️  Existente: {brand_name}')
                
                # ==================== PRODUCTOS ====================
                self.stdout.write(f'\n📦 Creando {NUM_PRODUCTS} Productos...')
                product_prefixes = {
                    'Refrigeración': [
                        'Refrigerador Side by Side', 'Refrigerador Top Mount', 'Refrigerador Bottom Freezer',
                        'Congelador Vertical', 'Congelador Horizontal', 'Minibar'
                    ],
                    'Lavado y Secado': [
                        'Lavadora Carga Frontal', 'Lavadora Carga Superior', 'Lavadora-Secadora',
                        'Secadora a Gas', 'Secadora Eléctrica', 'Lavavajillas'
                    ],
                    'Cocción': [
                        'Horno Eléctrico', 'Horno a Gas', 'Placa de Inducción', 'Placa Vitrocerámica',
                        'Cocina a Gas', 'Campana Extractora', 'Horno Microondas Integrado'
                    ],
                    'Pequeños Electrodomésticos Cocina': [
                        'Microondas', 'Cafetera de Goteo', 'Cafetera Espresso', 'Cafetera de Cápsulas',
                        'Tostadora', 'Sandwichera', 'Horno Eléctrico de Mesa'
                    ],
                    'Preparación de Alimentos': [
                        'Batidora de Mano', 'Batidora de Vaso', 'Licuadora', 'Procesador de Alimentos',
                        'Freidora de Aire', 'Robot de Cocina', 'Picadora', 'Extractor de Jugos'
                    ],
                    'Limpieza del Hogar': [
                        'Aspiradora de Trineo', 'Aspiradora Escoba', 'Aspiradora Robot', 'Aspiradora de Mano',
                        'Plancha a Vapor', 'Centro de Planchado', 'Vaporizador'
                    ],
                    'Climatización': [
                        'Ventilador de Torre', 'Ventilador de Pedestal', 'Ventilador de Techo',
                        'Calefactor Eléctrico', 'Calefactor a Gas', 'Aire Acondicionado Portátil'
                    ],
                    'Cuidado Personal': [
                        'Secador de Pelo', 'Plancha de Pelo', 'Rizador', 'Afeitadora Eléctrica',
                        'Máquina de Cortar Pelo', 'Cepillo de Dientes Eléctrico', 'Depiladora'
                    ],
                    'Televisores': [
                        'Smart TV LED', 'Smart TV OLED', 'Smart TV QLED', 'Smart TV 4K',
                        'Smart TV 8K', 'Televisor HD'
                    ],
                    'Audio': [
                        'Barra de Sonido', 'Altavoz Bluetooth', 'Minicomponente', 'Equipo de Sonido',
                        'Home Theater', 'Auriculares Inalámbricos', 'Parlante Portátil'
                    ],
                    'Computación': [
                        'Laptop', 'Tablet', 'Monitor LED', 'Monitor Curvo',
                        'All-in-One', 'Chromebook'
                    ]
                }
                
                price_ranges = {
                    'Refrigeración': (600, 3500),
                    'Lavado y Secado': (500, 2800),
                    'Cocción': (300, 2500),
                    'Pequeños Electrodomésticos Cocina': (50, 400),
                    'Preparación de Alimentos': (40, 600),
                    'Limpieza del Hogar': (80, 1200),
                    'Climatización': (60, 800),
                    'Cuidado Personal': (30, 250),
                    'Televisores': (400, 4500),
                    'Audio': (50, 1500),
                    'Computación': (350, 3500)
                }
                
                product_ids = []
                existing_products = Product.objects.count()
                
                for i in range(NUM_PRODUCTS):
                    category = Category.objects.get(id=random.choice(category_ids))
                    brand = Brand.objects.get(id=random.choice(brand_ids))
                    
                    prefix = random.choice(product_prefixes.get(category.name, ['Producto']))
                    model = f'Modelo {random.randint(100, 999)}'
                    name = f'{prefix} {brand.name} {model}'
                    
                    price_range = price_ranges.get(category.name, (50, 1000))
                    price = Decimal(str(random.uniform(*price_range))).quantize(Decimal('0.01'))
                    stock = random.randint(5, 50)
                    
                    product = Product.objects.create(
                        name=name,
                        description=fake.text(max_nb_chars=200),
                        price=price,
                        stock=stock,
                        category=category,
                        brand=brand
                    )
                    product_ids.append(product.id)
                    
                    if (i + 1) % 20 == 0:
                        self.stdout.write(f'  ✅ Creados {i + 1}/{NUM_PRODUCTS} productos...')
                
                self.stdout.write(self.style.SUCCESS(f'  ✅ Total productos: {existing_products + NUM_PRODUCTS}'))
                
                # ==================== CLIENTES ====================
                self.stdout.write(f'\n👥 Creando {NUM_CLIENTS} Clientes...')
                client_ids = []
                existing_clients = User.objects.filter(role__name='CLIENTE').count()
                
                for i in range(NUM_CLIENTS):
                    username = fake.user_name() + str(random.randint(100, 999))
                    email = f'{username}@{fake.domain_name()}'
                    
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password='password123',
                        first_name=fake.first_name(),
                        last_name=fake.last_name(),
                        role=role_cliente  # Asignar ForeignKey directamente
                    )
                    
                    ClientProfile.objects.create(
                        user=user,
                        full_name=f'{user.first_name} {user.last_name}',
                        phone_number=fake.phone_number(),
                        address=fake.address()
                    )
                    
                    client_ids.append(user.id)
                    
                    if (i + 1) % 30 == 0:
                        self.stdout.write(f'  ✅ Creados {i + 1}/{NUM_CLIENTS} clientes...')
                
                self.stdout.write(self.style.SUCCESS(f'  ✅ Total clientes: {existing_clients + NUM_CLIENTS}'))
                
                # ==================== ÓRDENES Y ORDER ITEMS ====================
                self.stdout.write('\n🛒 Creando Órdenes...')
                total_orders = 0
                total_items = 0
                
                all_product_ids = list(Product.objects.values_list('id', flat=True))
                
                for client_id in client_ids:
                    user = User.objects.get(id=client_id)
                    num_orders = random.randint(
                        max(1, AVG_ORDERS_PER_CLIENT - 5),
                        AVG_ORDERS_PER_CLIENT + 5
                    )
                    
                    for _ in range(num_orders):
                        # --- Lógica de Fecha con Picos de Temporada ---
                        days_range = (END_DATE - START_DATE).days
                        # Genera un día base aleatorio
                        random_days_base = random.randint(0, days_range)
                        temp_date = START_DATE + timedelta(days=random_days_base)

                        # Aumentar probabilidad de compras en Noviembre/Diciembre (temporada alta)
                        is_peak_season = temp_date.month in [11, 12]
                        if is_peak_season and random.random() < 0.4:
                            # Si es temporada alta y la probabilidad se cumple (40% chance extra),
                            # genera una nueva fecha dentro de la temporada alta de ese año
                            peak_year = temp_date.year
                            peak_start = datetime(peak_year, 11, 1, tzinfo=ZoneInfo("UTC"))
                            peak_end = datetime(peak_year, 12, 31, tzinfo=ZoneInfo("UTC"))
                            # Asegurar que esté dentro del rango general
                            peak_start = max(peak_start, START_DATE)
                            peak_end = min(peak_end, END_DATE)
                            if peak_start < peak_end:  # Evitar errores si el rango es inválido
                                peak_days_range = (peak_end - peak_start).days
                                random_peak_days = random.randint(0, peak_days_range)
                                created_at = peak_start + timedelta(days=random_peak_days)
                            else:
                                created_at = temp_date  # Fallback a la fecha original
                        else:
                            created_at = temp_date  # Usar la fecha aleatoria normal

                        # Asegurar que la fecha final no exceda END_DATE
                        created_at = min(created_at, END_DATE)
                        # --- Fin Lógica de Fecha ---
                        
                        # Crear orden
                        order = Order.objects.create(
                            user=user,
                            status='PAGADO',
                            payment_status='pagado',
                            total_price=Decimal('0.00'),
                            shipping_address=fake.address(),
                            shipping_phone=fake.phone_number(),
                            created_at=created_at
                        )
                        
                        # Crear items de la orden
                        num_items = random.randint(1, MAX_ITEMS_PER_ORDER)
                        order_total = Decimal('0.00')
                        
                        for _ in range(num_items):
                            product = Product.objects.get(id=random.choice(all_product_ids))
                            quantity = random.randint(1, 3)
                            price = product.price
                            
                            OrderItem.objects.create(
                                order=order,
                                product=product,
                                quantity=quantity,
                                price=price
                            )
                            
                            order_total += price * quantity
                            total_items += 1
                        
                        order.total_price = order_total
                        order.save()
                        total_orders += 1
                    
                    if (client_ids.index(client_id) + 1) % 30 == 0:
                        self.stdout.write(
                            f'  ✅ Procesados {client_ids.index(client_id) + 1}/{NUM_CLIENTS} '
                            f'clientes ({total_orders} órdenes)...'
                        )
                
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ Total órdenes: {total_orders} con {total_items} items'
                ))
                
                # ==================== RESEÑAS ====================
                self.stdout.write('\n⭐ Creando Reseñas...')
                paid_items = OrderItem.objects.filter(order__status='PAGADO').select_related(
                    'order__user', 'product'
                )
                
                total_reviews = 0
                for item in paid_items:
                    if random.random() < REVIEW_CHANCE:
                        rating = random.choices(
                            [1, 2, 3, 4, 5],
                            weights=[5, 10, 20, 35, 30]  # Más peso a ratings altos
                        )[0]
                        
                        comments = {
                            5: ['Excelente producto', 'Muy buena calidad', 'Lo recomiendo'],
                            4: ['Buen producto', 'Cumple expectativas', 'Satisfecho con la compra'],
                            3: ['Aceptable', 'Producto normal', 'Nada especial'],
                            2: ['Regular', 'Esperaba más', 'No muy satisfecho'],
                            1: ['Mala calidad', 'No lo recomiendo', 'Decepcionante']
                        }
                        
                        comment = random.choice(comments[rating]) + '. ' + fake.sentence()
                        
                        review, created = Review.objects.get_or_create(
                            product=item.product,
                            user=item.order.user,
                            defaults={
                                'rating': rating,
                                'comment': comment
                            }
                        )
                        
                        if created:
                            total_reviews += 1
                
                self.stdout.write(self.style.SUCCESS(f'  ✅ Total reseñas: {total_reviews}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error: {str(e)}'))
            raise
        
        # Resumen final
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✅ GENERACIÓN DE DATOS COMPLETADA'))
        self.stdout.write('='*60)
        self.stdout.write(f'📊 Resumen:')
        self.stdout.write(f'  - Categorías: {Category.objects.count()}')
        self.stdout.write(f'  - Marcas: {Brand.objects.count()}')
        self.stdout.write(f'  - Productos: {Product.objects.count()}')
        self.stdout.write(f'  - Clientes: {User.objects.filter(role__name="CLIENTE").count()}')
        self.stdout.write(f'  - Órdenes: {Order.objects.count()}')
        self.stdout.write(f'  - Items de Orden: {OrderItem.objects.count()}')
        self.stdout.write(f'  - Reseñas: {Review.objects.count()}')
        self.stdout.write('='*60)
