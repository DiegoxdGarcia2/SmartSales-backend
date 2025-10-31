from django.urls import path
from .views import (
    SalesPredictionView,
    SalesHistoryByMonthView,
    SalesHistoryByCategoryView,
    FrequentlyBoughtTogetherView,
    ComplementaryCategoryRecsView,
    DashboardKpiView
)

app_name = 'analytics'

urlpatterns = [
    path('predictions/sales/monthly/', SalesPredictionView.as_view(), name='sales-predictions-monthly'),
    path('sales_by_month/', SalesHistoryByMonthView.as_view(), name='sales-history-by-month'),
    path('sales_by_category/', SalesHistoryByCategoryView.as_view(), name='sales-history-by-category'),
    path('recommendations/frequently_bought_together/', FrequentlyBoughtTogetherView.as_view(), name='recommendations-fbt'),
    path('recommendations/complementary_category/', ComplementaryCategoryRecsView.as_view(), name='recommendations-complementary'),
    path('kpis/', DashboardKpiView.as_view(), name='dashboard-kpis'),
]
