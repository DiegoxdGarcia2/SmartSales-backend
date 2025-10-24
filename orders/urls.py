from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartView, OrderViewSet, CreateCheckoutSessionView, StripeWebhookView

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('stripe/create-checkout-session/', CreateCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('', include(router.urls)),
]
