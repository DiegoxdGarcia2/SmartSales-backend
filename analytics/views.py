import os
import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly
from django.conf import settings
from django.db.models import F, Sum
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
        
        # Obtener detalles de los productos recomendados
        # Optimizar con select_related para evitar N+1 queries
        recommended_products = Product.objects.filter(
            id__in=recommended_ids
        ).select_related('brand', 'category')
        
        # Limitar a las primeras 3 recomendaciones
        recommended_products = recommended_products[:3]
        
        # Serializar productos
        serializer = ProductSerializer(
            recommended_products,
            many=True,
            context={'request': request}
        )
        
        logger.info(f"Devolviendo {len(serializer.data)} recomendaciones para product_id={product_id}")
        
        return Response(serializer.data, status=status.HTTP_200_OK)
