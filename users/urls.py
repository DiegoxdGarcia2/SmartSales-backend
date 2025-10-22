from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, ClientProfileViewSet, RoleViewSet, UserViewSet

app_name = 'users'

router = DefaultRouter()
router.register(r'profiles', ClientProfileViewSet, basename='clientprofile')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]
