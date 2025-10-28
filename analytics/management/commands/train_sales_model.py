"""
Comando de Django para entrenar el modelo de predicción de ventas.
Carga datos históricos de órdenes pagadas, preprocesa, y entrena RandomForestRegressor.
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
import joblib

from orders.models import Order, OrderItem


class Command(BaseCommand):
    help = 'Entrena el modelo de predicción de ventas usando RandomForestRegressor'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🤖 ENTRENAMIENTO DEL MODELO DE PREDICCIÓN DE VENTAS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        # ==================== CARGAR DATOS ====================
        self.stdout.write('\n📊 Cargando datos de órdenes pagadas...')
        
        qs = OrderItem.objects.filter(
            order__status='PAGADO'
        ).select_related('order', 'product', 'product__category')
        
        data = list(qs.values(
            'order__created_at',
            'quantity',
            'price',
            'product__category__name',
            'product_id'
        ))
        
        if not data:
            self.stdout.write(self.style.ERROR('❌ No hay datos de ventas pagadas para entrenar.'))
            return
        
        self.stdout.write(f'✅ Cargados {len(data)} items de órdenes pagadas.')
        
        # ==================== PREPROCESAMIENTO ====================
        self.stdout.write('\n🔧 Preprocesando datos...')
        
        df = pd.DataFrame(data)
        df['order__created_at'] = pd.to_datetime(df['order__created_at'])
        df['total_item_price'] = df['quantity'] * df['price']
        
        # ==================== AGREGACIÓN POR MES ====================
        self.stdout.write('📅 Agregando datos por mes...')
        
        df.set_index('order__created_at', inplace=True)
        monthly_sales = df['total_item_price'].resample('ME').sum().reset_index()
        monthly_sales.rename(
            columns={'order__created_at': 'month', 'total_item_price': 'total_sales'},
            inplace=True
        )
        
        # Asegurar índice de fechas completo y rellenar meses sin ventas con 0
        monthly_sales.set_index('month', inplace=True)
        full_date_range = pd.date_range(
            start=monthly_sales.index.min(),
            end=monthly_sales.index.max(),
            freq='ME'
        )
        monthly_sales = monthly_sales.reindex(full_date_range, fill_value=0).reset_index()
        monthly_sales.rename(columns={'index': 'month'}, inplace=True)
        
        self.stdout.write(f'✅ Datos agregados por mes: {len(monthly_sales)} registros.')
        
        # ==================== FEATURE ENGINEERING ====================
        self.stdout.write('\n⚙️  Creando features...')
        
        # Features temporales
        monthly_sales['year'] = monthly_sales['month'].dt.year
        monthly_sales['month_num'] = monthly_sales['month'].dt.month
        
        # Lags (ventas meses anteriores)
        for i in range(1, 7):  # Usar lags de 1 a 6 meses
            monthly_sales[f'sales_lag_{i}'] = monthly_sales['total_sales'].shift(i)
        
        # Promedio móvil
        monthly_sales['sales_rolling_mean_3'] = monthly_sales['total_sales'].shift(1).rolling(window=3).mean()
        monthly_sales['sales_rolling_mean_6'] = monthly_sales['total_sales'].shift(1).rolling(window=6).mean()
        
        # Eliminar filas con NaN (debido a lags y rolling)
        monthly_sales.dropna(inplace=True)
        
        self.stdout.write(f'✅ Features creadas. Datos listos: {len(monthly_sales)} registros.')
        
        # ==================== DEFINIR X e y ====================
        features = [
            'year', 'month_num',
            'sales_lag_1', 'sales_lag_2', 'sales_lag_3',
            'sales_lag_4', 'sales_lag_5', 'sales_lag_6',
            'sales_rolling_mean_3', 'sales_rolling_mean_6'
        ]
        target = 'total_sales'
        
        X = monthly_sales[features]
        y = monthly_sales[target]
        
        if X.empty or len(X) < 10:
            self.stdout.write(self.style.ERROR(
                '❌ No hay suficientes datos después del preprocesamiento para entrenar/evaluar.'
            ))
            return
        
        # ==================== DIVIDIR DATOS ====================
        self.stdout.write('\n✂️  Dividiendo datos (80% entrenamiento, 20% prueba)...')
        
        # Dividir cronológicamente para series temporales
        split_index = int(len(X) * 0.8)
        X_train, X_test = X[:split_index], X[split_index:]
        y_train, y_test = y[:split_index], y[split_index:]
        
        self.stdout.write(f'✅ Datos divididos: {len(X_train)} entrenamiento, {len(X_test)} prueba.')
        
        # ==================== ENTRENAR MODELO ====================
        self.stdout.write('\n🎯 Entrenando RandomForestRegressor...')
        
        model = RandomForestRegressor(
            n_estimators=150,
            random_state=42,
            n_jobs=-1,
            max_depth=10,
            min_samples_split=5
        )
        
        model.fit(X_train, y_train)
        
        self.stdout.write(self.style.SUCCESS('✅ Modelo entrenado exitosamente.'))
        
        # ==================== EVALUAR MODELO ====================
        self.stdout.write('\n📈 Evaluando modelo...')
        
        y_pred = model.predict(X_test)
        
        # RMSE
        mse = mean_squared_error(y_test, y_pred)
        rmse = mse ** 0.5
        self.stdout.write(f'  📊 RMSE (Root Mean Squared Error): ${rmse:,.2f}')
        
        # MAPE (evitar división por cero)
        if (y_test > 0).all():
            mape = mean_absolute_percentage_error(y_test, y_pred) * 100
            self.stdout.write(f'  📊 MAPE (Mean Absolute Percentage Error): {mape:.2f}%')
        
        # Comparación muestra
        self.stdout.write('\n📋 Muestra de predicciones vs valores reales:')
        comparison = pd.DataFrame({
            'Real': y_test.values[:5],
            'Predicción': y_pred[:5]
        })
        self.stdout.write(str(comparison))
        
        # ==================== GUARDAR MODELO ====================
        self.stdout.write('\n💾 Guardando modelo entrenado...')
        
        MODEL_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
        MODEL_PATH = os.path.join(MODEL_DIR, 'sales_model.joblib')
        
        os.makedirs(MODEL_DIR, exist_ok=True)
        
        # Guardar modelo y metadata
        model_data = {
            'model': model,
            'features': features,
            'trained_at': timezone.now(),
            'rmse': rmse,
            'mape': mape if (y_test > 0).all() else None,
            'n_train_samples': len(X_train),
            'n_test_samples': len(X_test)
        }
        
        joblib.dump(model_data, MODEL_PATH)
        
        self.stdout.write(self.style.SUCCESS(f'✅ Modelo guardado en: {MODEL_PATH}'))
        
        # ==================== RESUMEN FINAL ====================
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('✅ ENTRENAMIENTO COMPLETADO'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'📊 Resumen:')
        self.stdout.write(f'  - Total de registros mensuales: {len(monthly_sales)}')
        self.stdout.write(f'  - Features utilizadas: {len(features)}')
        self.stdout.write(f'  - Datos de entrenamiento: {len(X_train)}')
        self.stdout.write(f'  - Datos de prueba: {len(X_test)}')
        self.stdout.write(f'  - RMSE: ${rmse:,.2f}')
        if (y_test > 0).all():
            self.stdout.write(f'  - MAPE: {mape:.2f}%')
        self.stdout.write(f'  - Modelo guardado: {MODEL_PATH}')
        self.stdout.write('=' * 70)
