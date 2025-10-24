from rest_framework import viewsets, permissions, serializers as drf_serializers
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.exceptions import PermissionDenied
from .models import Category, Product, Brand, Review
from .serializers import CategorySerializer, ProductSerializer, BrandSerializer, ReviewSerializer
from .permissions import HasPurchasedProduct, IsReviewAuthorOrReadOnly


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


class BrandViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las marcas de productos.
    GET: Todos pueden ver
    POST, PUT, PATCH, DELETE: Solo administradores
    """
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
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
        Opcionalmente filtra productos por categoría o marca usando query params.
        Ejemplo: /api/products/?category=1&brand=2
        """
        queryset = Product.objects.all()
        category_id = self.request.query_params.get('category', None)
        brand_id = self.request.query_params.get('brand', None)
        
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)
        
        if brand_id is not None:
            queryset = queryset.filter(brand_id=brand_id)
        
        return queryset


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las reseñas de productos.
    GET: Todos pueden ver
    POST: Usuario autenticado que haya comprado el producto
    PUT, PATCH, DELETE: Solo el autor de la reseña
    """
    queryset = Review.objects.all().select_related('user', 'product')
    serializer_class = ReviewSerializer

    def get_queryset(self):
        """
        Opcional: Filtrar reseñas por producto si se pasa ?product_id=X en la URL
        """
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        """
        Asigna el usuario automáticamente y valida que haya comprado el producto
        """
        user = self.request.user
        product_id = serializer.validated_data['product'].id

        # Validar si el usuario compró el producto ANTES de guardar
        if not HasPurchasedProduct.check_purchase(user, product_id):
            raise PermissionDenied(HasPurchasedProduct.message)

        # Validar si ya existe una reseña de este usuario para este producto
        if Review.objects.filter(product_id=product_id, user=user).exists():
            raise drf_serializers.ValidationError('Ya has dejado una reseña para este producto.')

        serializer.save(user=user)

    def get_permissions(self):
        """
        Asigna permisos según la acción
        """
        # GET (list, retrieve): Cualquiera puede leer
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        # POST (create): Usuario autenticado (validación de compra en perform_create)
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        # PUT, PATCH, DELETE: Solo el autor de la reseña
        else:
            permission_classes = [IsReviewAuthorOrReadOnly]
        return [permission() for permission in permission_classes]
