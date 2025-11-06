import logging
from django.db.models import Q, Sum, Count, F, Avg
from django.db.models.functions import TruncMonth
from orders.models import Order, OrderItem
from products.models import Product, Category, Brand, Review
from users.models import User

logger = logging.getLogger(__name__)

def build_report_query(options: dict):
    """
    Construye un QuerySet dinámico y headers basado en las opciones del parser.
    
    Args:
        options (dict): Diccionario con opciones parseadas del prompt:
            - module (str): 'ventas', 'productos', 'clientes', 'reseñas'
            - filters (dict): Filtros de texto (brand_name, category_name, user_username)
            - group_by (str): Agrupación (mes, category, brand, product, user)
            - start_date (datetime): Fecha inicio del rango
            - end_date (datetime): Fecha fin del rango
    
    Returns:
        tuple: (queryset, headers)
            - queryset: QuerySet de Django con los datos filtrados y agrupados
            - headers: Lista de strings con los nombres de las columnas del reporte
    """
    module = options.get('module')
    filters = options.get('filters', {})
    group_by = options.get('group_by')
    start_date = options.get('start_date')
    end_date = options.get('end_date')

    queryset = None
    headers = []

    # --- MÓDULO VENTAS ---
    if module == 'ventas':
        queryset = OrderItem.objects.filter(order__status='PAGADO')  # Base
        
        # --- APLICAR FILTROS PRIMERO (antes de agrupación) ---
        q_filters = Q()
        
        # Filtros de Fecha
        if start_date and end_date:
            q_filters &= Q(order__created_at__range=(start_date, end_date))
        
        # Filtros de Texto
        if 'brand_name' in filters:
            q_filters &= Q(product__brand__name__icontains=filters['brand_name'])
        if 'category_name' in filters:
            q_filters &= Q(product__category__name__icontains=filters['category_name'])
        if 'user_username' in filters:
            q_filters &= Q(order__user__username__icontains=filters['user_username'])
        
        queryset = queryset.filter(q_filters)
        # --- FIN FILTROS ---

        # Aplicar Agrupación
        if group_by == 'mes':
            queryset = queryset.annotate(
                group=TruncMonth('order__created_at')
            ).values('group').annotate(
                total_ventas=Sum(F('quantity') * F('price')),
                total_unidades=Sum('quantity'),
                total_ordenes=Count('order__id', distinct=True)
            ).order_by('group')[:120]  # Máximo 120 meses (10 años)
            headers = ['Mes', 'Ventas Totales', 'Unidades Vendidas', 'Órdenes']
        
        elif group_by == 'category':
            queryset = queryset.values('product__category__name').annotate(
                total_ventas=Sum(F('quantity') * F('price')),
                total_unidades=Sum('quantity')
            ).order_by('-total_ventas')[:1000]  # Máximo 1000 categorías
            headers = ['Categoría', 'Ventas Totales', 'Unidades Vendidas']
        
        elif group_by == 'brand':
            queryset = queryset.values('product__brand__name').annotate(
                total_ventas=Sum(F('quantity') * F('price')),
                total_unidades=Sum('quantity')
            ).order_by('-total_ventas')[:1000]  # Máximo 1000 marcas
            headers = ['Marca', 'Ventas Totales', 'Unidades Vendidas']
        
        elif group_by == 'product':
            queryset = queryset.values('product__name').annotate(
                total_ventas=Sum(F('quantity') * F('price')),
                total_unidades=Sum('quantity')
            ).order_by('-total_ventas')[:5000]  # Máximo 5000 productos
            headers = ['Producto', 'Ventas Totales', 'Unidades Vendidas']

        elif group_by == 'user':
            queryset = queryset.values('order__user__username').annotate(
                total_ventas=Sum(F('quantity') * F('price')),
                total_ordenes=Count('order__id', distinct=True)
            ).order_by('-total_ventas')[:5000]  # Máximo 5000 clientes
            headers = ['Cliente (Username)', 'Ventas Totales', 'Órdenes Realizadas']

        else:  # Reporte detallado de items de ventas (sin agrupar)
            # 🔧 LÍMITE DE SEGURIDAD: Máximo 10,000 registros para evitar out of memory
            queryset = queryset.select_related(
                'order', 'order__user', 'product', 'product__category', 'product__brand'
            ).order_by('-order__created_at')[:10000].values(
                'order__id',
                'order__created_at',
                'order__user__username',
                'product__name',
                'product__category__name',
                'product__brand__name',
                'quantity',
                'price',
            )
            headers = ['ID Orden', 'Fecha', 'Cliente', 'Producto', 'Categoría', 'Marca', 'Cantidad', 'Precio']
            logger.info(f"Reporte detallado de ventas limitado a 10,000 registros para proteger memoria")

    # --- MÓDULO PRODUCTOS ---
    elif module == 'productos':
        queryset = Product.objects.all()
        
        # --- APLICAR FILTROS PRIMERO (antes de agrupación) ---
        q_filters = Q()
        
        # Filtros de Fecha (fecha de creación del producto)
        if start_date and end_date:
            q_filters &= Q(created_at__range=(start_date, end_date))
        
        # Filtros de Texto
        if 'brand_name' in filters:
            q_filters &= Q(brand__name__icontains=filters['brand_name'])
        if 'category_name' in filters:
            q_filters &= Q(category__name__icontains=filters['category_name'])
        
        queryset = queryset.filter(q_filters)
        # --- FIN FILTROS ---

        if group_by == 'brand':
            queryset = queryset.values('brand__name').annotate(
                conteo_productos=Count('id'),
                stock_total=Sum('stock'),
                precio_promedio=Avg('price')
            ).order_by('-conteo_productos')[:1000]  # Máximo 1000 marcas
            headers = ['Marca', 'Nro. Productos', 'Stock Total', 'Precio Promedio']
        
        elif group_by == 'category':
            queryset = queryset.values('category__name').annotate(
                conteo_productos=Count('id'),
                stock_total=Sum('stock'),
                precio_promedio=Avg('price')
            ).order_by('-conteo_productos')[:1000]  # Máximo 1000 categorías
            headers = ['Categoría', 'Nro. Productos', 'Stock Total', 'Precio Promedio']
        
        else:  # Reporte detallado de productos
            # 🔧 LÍMITE DE SEGURIDAD: Máximo 5,000 productos
            queryset = queryset.select_related('category', 'brand').order_by('name')[:5000].values(
                'name', 'category__name', 'brand__name', 'price', 'stock', 'created_at'
            )
            headers = ['Producto', 'Categoría', 'Marca', 'Precio', 'Stock', 'Fecha Creación']
            logger.info(f"Reporte detallado de productos limitado a 5,000 registros")

    # --- MÓDULO CLIENTES ---
    elif module == 'clientes':
        queryset = User.objects.filter(role__name='CLIENTE')
        
        if start_date and end_date:  # Filtrar por fecha de registro
            queryset = queryset.filter(date_joined__range=(start_date, end_date))
        
        if 'user_username' in filters:
            queryset = queryset.filter(username__icontains=filters['user_username'])
        
        # (Agrupación no muy relevante aquí, solo listado)
        # 🔧 LÍMITE DE SEGURIDAD: Máximo 5,000 clientes
        queryset = queryset.select_related('client_profile').order_by('-date_joined')[:5000].values(
            'username', 'email', 'first_name', 'last_name', 'date_joined', 'client_profile__phone_number'
        )
        headers = ['Username', 'Email', 'Nombre', 'Apellido', 'Fecha Registro', 'Teléfono']
        logger.info(f"Reporte detallado de clientes limitado a 5,000 registros")

    # --- MÓDULO RESEÑAS ---
    elif module == 'reseñas':
        queryset = Review.objects.all()

        # --- APLICAR FILTROS PRIMERO (antes de agrupación) ---
        q_filters = Q()
        
        # Filtros de Fecha
        if start_date and end_date:
            q_filters &= Q(created_at__range=(start_date, end_date))

        # Filtros de Texto
        if 'brand_name' in filters:
            q_filters &= Q(product__brand__name__icontains=filters['brand_name'])
        if 'category_name' in filters:
            q_filters &= Q(product__category__name__icontains=filters['category_name'])
        if 'user_username' in filters:
            q_filters &= Q(user__username__icontains=filters['user_username'])
        
        queryset = queryset.filter(q_filters)
        # --- FIN FILTROS ---
        
        if group_by == 'product':
            queryset = queryset.values('product__name').annotate(
                conteo_reseñas=Count('id'),
                rating_promedio=Avg('rating')
            ).order_by('-conteo_reseñas')[:5000]  # Máximo 5000 productos
            headers = ['Producto', 'Nro. Reseñas', 'Rating Promedio']

        else:  # Reporte detallado de reseñas
            # 🔧 LÍMITE DE SEGURIDAD: Máximo 10,000 reseñas
            queryset = queryset.select_related('product', 'user').order_by('-created_at')[:10000].values(
                'created_at', 'product__name', 'user__username', 'rating', 'comment', 'sentiment'
            )
            headers = ['Fecha', 'Producto', 'Cliente', 'Rating', 'Comentario', 'Sentimiento']
            logger.info(f"Reporte detallado de reseñas limitado a 10,000 registros")
    
    logger.info(f"Query builder generó {queryset.count() if queryset else 0} resultados para el módulo {module}.")
    return queryset, headers
