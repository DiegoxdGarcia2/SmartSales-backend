from django.urls import path
from .views import DynamicReportAPIView

app_name = 'reports'

urlpatterns = [
    path('dynamic_report/', DynamicReportAPIView.as_view(), name='dynamic-report'),
]
