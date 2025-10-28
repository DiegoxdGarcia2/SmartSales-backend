from django.urls import path
from .views import SalesPredictionView

app_name = 'analytics'

urlpatterns = [
    path('predictions/sales/monthly/', SalesPredictionView.as_view(), name='sales-predictions-monthly'),
]
