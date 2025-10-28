from django.urls import path
from .views import (
    SalesPredictionView,
    SalesHistoryByMonthView,
    SalesHistoryByCategoryView
)

app_name = 'analytics'

urlpatterns = [
    path('predictions/sales/monthly/', SalesPredictionView.as_view(), name='sales-predictions-monthly'),
    path('sales_by_month/', SalesHistoryByMonthView.as_view(), name='sales-history-by-month'),
    path('sales_by_category/', SalesHistoryByCategoryView.as_view(), name='sales-history-by-category'),
]
