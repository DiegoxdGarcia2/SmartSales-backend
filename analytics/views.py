import os
import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from django.conf import settings
from django.db.models import F, Sum
from django.db.models.functions import TruncMonth
from orders.models import OrderItem
from products.models import Category

# Configurar logger
logger = logging.getLogger(__name__)

# Rutas de archivos ML
MODEL_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
PREDICTIONS_PATH = os.path.join(MODEL_DIR, 'predictions.json')


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
