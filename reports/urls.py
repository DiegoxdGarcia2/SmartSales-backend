from django.urls import path
from .views import DynamicReportAPIView
from .voice_view import VoiceReportAPIView

app_name = 'reports'

urlpatterns = [
    path('dynamic_report/', DynamicReportAPIView.as_view(), name='dynamic-report'),
    path('voice_report/', VoiceReportAPIView.as_view(), name='voice-report'),
]
