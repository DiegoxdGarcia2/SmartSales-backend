import os
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import F, Sum
from django.db.models.functions import TruncMonth
from orders.models import Order, OrderItem
from products.models import Category

# NO importar pandas y joblib aquí - se cargarán solo cuando se necesiten
# Esto reduce el uso de memoria en el servidor

# Configurar logger
logger = logging.getLogger(__name__)

# Ruta del modelo entrenado
MODEL_PATH = os.path.join(settings.BASE_DIR, 'ml_models', 'sales_model.joblib')


class SalesPredictionView(APIView):
    """
    Vista para obtener predicciones de ventas mensuales futuras.
    Solo accesible para administradores.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, format=None):
        """
        Predice las ventas mensuales para los próximos N meses.
        """
        try:
            # Importar pandas y joblib solo cuando se necesiten (lazy loading)
            # Esto reduce el uso de memoria del servidor
            import pandas as pd
            import joblib
            
            # ========== 1. CARGAR MODELO ==========
            if not os.path.exists(MODEL_PATH):
                return Response(
                    {
                        'error': 'Modelo no entrenado aún',
                        'message': 'Por favor ejecute el comando train_sales_model primero'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            try:
                model_data = joblib.load(MODEL_PATH)
                model = model_data['model']
            except Exception as e:
                return Response(
                    {
                        'error': 'Error al cargar el modelo',
                        'details': str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # ========== 2. OBTENER ÚLTIMOS DATOS HISTÓRICOS ==========
            # Replicamos la lógica del comando train_sales_model para obtener datos actualizados
            order_items = OrderItem.objects.filter(
                order__payment_status='pagado'
            ).annotate(
                total=F('price') * F('quantity')
            ).values('order__created_at', 'total')

            if not order_items.exists():
                return Response(
                    {
                        'error': 'No hay datos de órdenes pagadas',
                        'message': 'Se necesitan datos históricos para generar predicciones'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Convertir a DataFrame
            df = pd.DataFrame(list(order_items))
            df.rename(columns={'order__created_at': 'date', 'total': 'sales'}, inplace=True)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

            # Agregar por mes
            monthly_sales = df['sales'].resample('ME').sum().reset_index()
            monthly_sales.columns = ['month', 'total_sales']

            if len(monthly_sales) < 10:
                return Response(
                    {
                        'error': 'Datos insuficientes',
                        'message': f'Se necesitan al menos 10 meses de datos. Actualmente hay {len(monthly_sales)} meses.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Obtener el último mes conocido y sus datos
            last_known_data = monthly_sales.iloc[-1].copy()
            last_month = last_known_data['month']

            # ========== 3. PREPARAR FEATURES INICIALES ==========
            # Crear features de lags y rolling means para el último mes conocido
            monthly_sales['year'] = monthly_sales['month'].dt.year
            monthly_sales['month_num'] = monthly_sales['month'].dt.month

            # Crear lags
            for i in range(1, 7):
                monthly_sales[f'sales_lag_{i}'] = monthly_sales['total_sales'].shift(i)

            # Crear promedios móviles
            monthly_sales['sales_rolling_mean_3'] = monthly_sales['total_sales'].rolling(window=3).mean()
            monthly_sales['sales_rolling_mean_6'] = monthly_sales['total_sales'].rolling(window=6).mean()

            # Eliminar filas con NaN (primeros 6 meses no tendrán todos los lags)
            monthly_sales_clean = monthly_sales.dropna()

            if len(monthly_sales_clean) == 0:
                return Response(
                    {
                        'error': 'Datos insuficientes después del preprocesamiento',
                        'message': 'Se necesitan al menos 6 meses de datos para generar features'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Obtener las features del último registro válido
            last_valid_data = monthly_sales_clean.iloc[-1].to_dict()
            current_features = {
                'year': int(last_valid_data['year']),
                'month_num': int(last_valid_data['month_num']),
                'sales_lag_1': float(last_valid_data['sales_lag_1']),
                'sales_lag_2': float(last_valid_data['sales_lag_2']),
                'sales_lag_3': float(last_valid_data['sales_lag_3']),
                'sales_lag_4': float(last_valid_data['sales_lag_4']),
                'sales_lag_5': float(last_valid_data['sales_lag_5']),
                'sales_lag_6': float(last_valid_data['sales_lag_6']),
                'sales_rolling_mean_3': float(last_valid_data['sales_rolling_mean_3']),
                'sales_rolling_mean_6': float(last_valid_data['sales_rolling_mean_6'])
            }

            # ========== 4. GENERAR PREDICCIONES FUTURAS ==========
            PREDICT_MONTHS = 6
            predictions = []
            features_order = [
                'year', 'month_num',
                'sales_lag_1', 'sales_lag_2', 'sales_lag_3',
                'sales_lag_4', 'sales_lag_5', 'sales_lag_6',
                'sales_rolling_mean_3', 'sales_rolling_mean_6'
            ]

            # Obtener el último mes válido del DataFrame limpio
            last_valid_month = monthly_sales_clean['month'].iloc[-1]

            for i in range(PREDICT_MONTHS):
                # Calcular el siguiente mes
                next_month = last_valid_month + relativedelta(months=i+1)

                # Actualizar features temporales
                current_features['year'] = next_month.year
                current_features['month_num'] = next_month.month

                # Preparar input para el modelo
                input_df = pd.DataFrame([current_features], columns=features_order)

                # Realizar predicción
                predicted_sales = model.predict(input_df)[0]

                # Guardar predicción
                predictions.append({
                    'month': next_month.strftime('%Y-%m-%d'),
                    'predicted_sales': round(float(predicted_sales), 2)
                })

                # ========== 5. ACTUALIZAR FEATURES PARA SIGUIENTE ITERACIÓN ==========
                # Desplazar lags: lag_6 = lag_5, lag_5 = lag_4, ..., lag_1 = predicción actual
                new_features = current_features.copy()
                
                for j in range(6, 1, -1):
                    new_features[f'sales_lag_{j}'] = new_features[f'sales_lag_{j-1}']
                
                new_features['sales_lag_1'] = predicted_sales

                # Recalcular promedios móviles
                last_3_sales = [
                    new_features['sales_lag_1'],
                    new_features['sales_lag_2'],
                    new_features['sales_lag_3']
                ]
                new_features['sales_rolling_mean_3'] = sum(last_3_sales) / 3

                last_6_sales = [new_features[f'sales_lag_{k}'] for k in range(1, 7)]
                new_features['sales_rolling_mean_6'] = sum(last_6_sales) / 6

                current_features = new_features

            # ========== 6. DEVOLVER RESPUESTA ==========
            return Response({
                'predictions': predictions,
                'model_info': {
                    'last_historical_month': last_valid_month.strftime('%Y-%m-%d'),
                    'prediction_months': PREDICT_MONTHS,
                    'model_path': MODEL_PATH
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    'error': 'Error al generar predicciones',
                    'details': str(e)
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
