from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, ClientProfileViewSet

app_name = 'users'

router = DefaultRouter()
router.register(r'profiles', ClientProfileViewSet, basename='clientprofile')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]
