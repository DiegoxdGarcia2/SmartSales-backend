"""
URLs para el sistema de ofertas de SmartSales.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OfferViewSet,
    OfferProductViewSet,
    UserOfferInteractionViewSet,
    OfferRecommendationViewSet
)

# Crear router
router = DefaultRouter()

# Registrar viewsets
router.register(r'offers', OfferViewSet, basename='offer')
router.register(r'offer-products', OfferProductViewSet, basename='offer-product')
router.register(r'interactions', UserOfferInteractionViewSet, basename='offer-interaction')
router.register(r'recommendations', OfferRecommendationViewSet, basename='offer-recommendation')

# URLs
urlpatterns = [
    path('', include(router.urls)),
]
