from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAdminUser, AllowAny
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso personalizado: Admin puede hacer todo, otros solo pueden leer.
    """
    def has_permission(self, request, view):
        # Permitir peticiones de lectura (GET, HEAD, OPTIONS) a todos
        if request.method in permissions.SAFE_METHODS:
            return True
        # Permitir escritura solo a administradores
        return request.user and request.user.is_staff


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las categorías de productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar los productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_queryset(self):
        """
        Opcionalmente filtra productos por categoría usando query params.
        Ejemplo: /api/products/?category=1
        """
        queryset = Product.objects.all()
        category_id = self.request.query_params.get('category', None)
        
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)
        
        return queryset
