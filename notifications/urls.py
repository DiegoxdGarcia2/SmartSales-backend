"""
URLs para la API de notificaciones
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet,
    NotificationPreferenceView,
    DeviceTokenViewSet,
    TestNotificationView
)

# Router para ViewSets
router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'fcm-tokens', DeviceTokenViewSet, basename='fcm-token')

urlpatterns = [
    # Preferencias de notificaciones
    path('preferences/', NotificationPreferenceView.as_view(), name='notification-preferences'),
    
    # Endpoint de prueba
    path('test/', TestNotificationView.as_view(), name='test-notification'),
    
    # ViewSets (notificaciones y tokens)
    path('', include(router.urls)),
]
