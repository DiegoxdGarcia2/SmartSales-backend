from django.urls import path
from .views import (
    SalesPredictionView,
    SalesHistoryByMonthView,
    SalesHistoryByCategoryView,
    FrequentlyBoughtTogetherView,
    ComplementaryCategoryRecsView,
    DashboardKpiView,
    TrainSalesModelView,
    ModelInfoView
)

app_name = 'analytics'

urlpatterns = [
    # Predicciones y ML
    path('predictions/sales/monthly/', SalesPredictionView.as_view(), name='sales-predictions-monthly'),
    path('train-model/', TrainSalesModelView.as_view(), name='train-sales-model'),
    path('model-info/', ModelInfoView.as_view(), name='model-info'),
    
    # Históricos
    path('sales_by_month/', SalesHistoryByMonthView.as_view(), name='sales-history-by-month'),
    path('sales_by_category/', SalesHistoryByCategoryView.as_view(), name='sales-history-by-category'),
    
    # Recomendaciones
    path('recommendations/frequently_bought_together/', FrequentlyBoughtTogetherView.as_view(), name='recommendations-fbt'),
    path('recommendations/complementary_category/', ComplementaryCategoryRecsView.as_view(), name='recommendations-complementary'),
    
    # KPIs
    path('kpis/', DashboardKpiView.as_view(), name='dashboard-kpis'),
]
