import os
import json
import logging
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly
from django.conf import settings
from django.db.models import F, Sum, Count, Q, Avg
from django.db.models.functions import TruncMonth
from orders.models import OrderItem
from products.models import Category, Product
from products.serializers import ProductSerializer

# Configurar logger
logger = logging.getLogger(__name__)

# Rutas de archivos ML
MODEL_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
PREDICTIONS_PATH = os.path.join(MODEL_DIR, 'predictions.json')
ASSOC_PATH = os.path.join(MODEL_DIR, 'product_associations.json')


class SalesPredictionView(APIView):
    """
    Vista para obtener predicciones de ventas mensuales futuras pre-calculadas.
    Lee las predicciones desde un archivo JSON generado por el comando train_sales_model.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, format=None):
        """
        Retorna las predicciones pre-calculadas desde el archivo JSON.
        """
        logger.info(f"Intentando leer predicciones desde {PREDICTIONS_PATH}")
        
        if not os.path.exists(PREDICTIONS_PATH):
            logger.warning("Archivo de predicciones no encontrado.")
            return Response(
                {
                    "detail": "Las predicciones aún no han sido generadas. Ejecute el comando de entrenamiento."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            with open(PREDICTIONS_PATH, 'r') as f:
                predictions = json.load(f)
            
            logger.info(f"Predicciones leídas exitosamente: {len(predictions)} meses.")
            
            # Devuelve directamente el contenido del JSON (que ya es una lista)
            return Response(predictions, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error al leer el archivo de predicciones: {e}", exc_info=True)
            return Response(
                {
                    "detail": "Error al leer las predicciones guardadas."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SalesHistoryByMonthView(APIView):
    """
    Vista para obtener ventas históricas agregadas por mes.
    Devuelve datos listos para gráficas.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, format=None):
        """
        Retorna ventas totales agregadas por mes.
        """
        logger.info('Calculando ventas históricas por mes...')
        
        try:
            # Agrupar OrderItems por mes y sumar el total
            monthly_sales_data = OrderItem.objects.filter(
                order__payment_status='pagado'  # Solo órdenes pagadas
            ).annotate(
                month=TruncMonth('order__created_at')  # Trunca la fecha al inicio del mes
            ).values(
                'month'  # Agrupa por mes
            ).annotate(
                total_sales=Sum(F('quantity') * F('price'))  # Suma cantidad * precio_historico
            ).order_by('month')  # Ordena cronológicamente

            # Formatear para la respuesta JSON que espera Recharts/Chart.js
            formatted_data = [
                {
                    # Formato 'YYYY-MM' ideal para etiquetas de eje X
                    "month": item['month'].strftime('%Y-%m'),
                    # Asegurar que sea número, no Decimal, para JSON y gráficas
                    "total_sales": float(item['total_sales'] or 0)
                }
                for item in monthly_sales_data
            ]
            
            logger.info(f'Ventas por mes calculadas: {len(formatted_data)} registros.')
            return Response(formatted_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f'Error al calcular ventas por mes: {str(e)}')
            return Response(
                {
                    'error': 'Error al calcular ventas por mes',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SalesHistoryByCategoryView(APIView):
    """
    Vista para obtener ventas históricas agregadas por categoría.
    Devuelve datos listos para gráficas.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, format=None):
        """
        Retorna ventas totales agregadas por categoría de producto.
        """
        logger.info('Calculando ventas históricas por categoría...')
        
        try:
            category_sales_data = OrderItem.objects.filter(
                order__payment_status='pagado',
                product__category__isnull=False  # Excluir items sin categoría
            ).values(
                'product__category__name'  # Agrupa por nombre de categoría
            ).annotate(
                total_sales=Sum(F('quantity') * F('price'))
            ).order_by('-total_sales')  # Ordenar por las más vendidas

            # Formatear para la respuesta JSON
            formatted_data = [
                {
                    "category": item['product__category__name'],
                    "total_sales": float(item['total_sales'] or 0)
                }
                for item in category_sales_data if item['product__category__name']  # Evitar nulos
            ]
            
            logger.info(f'Ventas por categoría calculadas: {len(formatted_data)} registros.')
            return Response(formatted_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f'Error al calcular ventas por categoría: {str(e)}')
            return Response(
                {
                    'error': 'Error al calcular ventas por categoría',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FrequentlyBoughtTogetherView(APIView):
    """
    Vista para obtener recomendaciones de productos frecuentemente comprados juntos.
    Lee las asociaciones desde ml_models/product_associations.json generado por generate_associations.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    # Cache de asociaciones en memoria (clase estática)
    _associations = None
    
    @classmethod
    def _load_associations(cls):
        """
        Carga las asociaciones de productos desde el archivo JSON.
        Cachea el resultado en memoria para evitar lecturas repetidas.
        """
        if cls._associations is None:
            logger.info(f"Cargando asociaciones de productos desde {ASSOC_PATH}")
            
            if not os.path.exists(ASSOC_PATH):
                logger.warning("Archivo de asociaciones no encontrado. Devolviendo diccionario vacío.")
                cls._associations = {}
                return {}
            
            try:
                with open(ASSOC_PATH, 'r') as f:
                    data = json.load(f)
                    # Convertir claves de string a int (JSON solo permite claves string)
                    cls._associations = {int(k): v for k, v in data.items()}
                
                logger.info(f"Asociaciones cargadas exitosamente: {len(cls._associations)} productos con recomendaciones.")
            
            except Exception as e:
                logger.error(f"Error al cargar/parsear asociaciones: {e}", exc_info=True)
                cls._associations = {}
        
        return cls._associations
    
    def get(self, request, format=None):
        """
        Obtiene productos recomendados para un product_id dado.
        Query param: product_id (int)
        """
        # Validar parámetro product_id
        product_id_str = request.query_params.get('product_id')
        
        if not product_id_str:
            return Response(
                {"detail": "Parámetro 'product_id' requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product_id = int(product_id_str)
        except ValueError:
            return Response(
                {"detail": "'product_id' debe ser un número entero."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cargar asociaciones (desde cache o archivo)
        associations = self._load_associations()
        
        # Buscar recomendaciones para el product_id
        recommended_ids = associations.get(product_id, [])
        
        if not recommended_ids:
            logger.info(f"No hay recomendaciones para product_id={product_id}")
            return Response([], status=status.HTTP_200_OK)
        
        # Seleccionar aleatoriamente 3 productos de las recomendaciones disponibles
        # Esto añade variedad y dinamismo a las recomendaciones
        if len(recommended_ids) > 3:
            # Si hay más de 3, selecciona 3 al azar
            sampled_ids = random.sample(recommended_ids, 3)
            logger.info(f"IDs seleccionados aleatoriamente: {sampled_ids} de {len(recommended_ids)} posibles.")
        else:
            # Si hay 3 o menos, tómalos todos
            sampled_ids = recommended_ids
            logger.info(f"Usando todos los IDs disponibles: {sampled_ids}")
        
        # Obtener detalles de los productos seleccionados
        # Optimizar con select_related para evitar N+1 queries
        recommended_products = Product.objects.filter(
            id__in=sampled_ids
        ).select_related('brand', 'category')
        
        # Serializar productos
        serializer = ProductSerializer(
            recommended_products,
            many=True,
            context={'request': request}
        )
        
        logger.info(f"Devolviendo {len(serializer.data)} recomendaciones para product_id={product_id}")
        
        return Response(serializer.data, status=status.HTTP_200_OK)


class ComplementaryCategoryRecsView(APIView):
    """
    Vista para obtener recomendaciones de productos complementarios basadas en categorías.
    Utiliza el mapeo COMPLEMENTARY_CATEGORIES de settings.py para encontrar categorías relacionadas.
    Retorna los productos más vendidos (populares) de esas categorías complementarias.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    MAX_RECOMMENDATIONS = 3  # Número máximo de productos a recomendar
    
    def get(self, request, format=None):
        """
        Obtiene productos populares de categorías complementarias.
        Query param: product_id (int)
        """
        # Validar parámetro product_id
        product_id_str = request.query_params.get('product_id')
        
        if not product_id_str:
            return Response(
                {"detail": "Parámetro 'product_id' requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product_id = int(product_id_str)
        except ValueError:
            return Response(
                {"detail": "'product_id' debe ser un número entero."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"Buscando recomendaciones complementarias para producto ID: {product_id}")
        
        try:
            # 1. Obtener el producto y su categoría
            current_product = Product.objects.select_related('category').only(
                'id', 'category__name'
            ).get(id=product_id)
            
            current_category_name = current_product.category.name if current_product.category else None
            
            if not current_category_name:
                logger.warning(f"Producto {product_id} no tiene categoría asignada.")
                return Response([], status=status.HTTP_200_OK)
            
            # 2. Obtener categorías complementarias del mapeo en settings
            complementary_category_names = settings.COMPLEMENTARY_CATEGORIES.get(
                current_category_name, []
            )
            
            if not complementary_category_names:
                logger.info(f"No hay categorías complementarias definidas para '{current_category_name}'.")
                return Response([], status=status.HTTP_200_OK)
            
            logger.debug(
                f"Categorías complementarias para '{current_category_name}': "
                f"{complementary_category_names}"
            )
            
            # 3. Encontrar los productos mejor calificados (por rating) en esas categorías
            # Calculamos el rating promedio de las reseñas de cada producto
            best_rated_products_query = Product.objects.filter(
                category__name__in=complementary_category_names  # Productos en categorías complementarias
            ).exclude(
                id=product_id  # Excluir el producto actual
            ).annotate(
                # Calcular el rating promedio de todas las reseñas
                average_rating=Avg('reviews__rating'),
                # Contar reseñas para asegurar que la calificación sea confiable
                reviews_count=Count('reviews')
            ).filter(
                # Filtrar: solo productos con al menos 1 reseña
                reviews_count__gt=0,
                average_rating__isnull=False  # Asegurar que tienen rating
            ).select_related(
                'brand', 'category'  # Optimizar carga de relaciones
            ).order_by(
                '-average_rating',  # Ordenar por mejor rating primero
                '-reviews_count'     # Desempate: más reseñas = más confiable
            )
            
            # 4. Limitar a los N mejor calificados
            recommended_products = list(best_rated_products_query[:self.MAX_RECOMMENDATIONS])
            
            logger.info(
                f"Encontrados {len(recommended_products)} productos complementarios mejor calificados "
                f"para '{current_category_name}'."
            )
            
            # 5. Serializar y devolver
            serializer = ProductSerializer(
                recommended_products,
                many=True,
                context={'request': request}
            )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Product.DoesNotExist:
            logger.warning(f"Producto {product_id} no encontrado en la base de datos.")
            return Response(
                {"detail": "Producto no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            logger.error(
                f"Error al generar recomendaciones complementarias para producto {product_id}: {e}",
                exc_info=True
            )
            return Response(
                {"detail": "Error al generar recomendaciones."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
