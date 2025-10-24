from rest_framework import permissions
from orders.models import Order, OrderItem
from .models import Review


class HasPurchasedProduct(permissions.BasePermission):
    """
    Permite escribir reseñas solo si el usuario ha comprado el producto.
    """
    message = 'Solo los usuarios que han comprado este producto pueden dejar una reseña.'

    def has_permission(self, request, view):
        # Permite GET a cualquiera
        if request.method in permissions.SAFE_METHODS:
            return True
        # Requiere autenticación para POST/PUT/DELETE
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Permite GET a cualquiera
        if request.method in permissions.SAFE_METHODS:
            return True
        # Permisos de escritura (PUT, DELETE): Solo el autor de la reseña puede modificarla/borrarla
        if isinstance(obj, Review):
            return obj.user == request.user

        # Permiso para crear (POST): Verifica si el usuario compró el producto.
        # Esta lógica se aplica mejor en el ViewSet al crear.
        # has_permission maneja la autenticación para POST.
        return True  # Simplificamos aquí, validación real en create()

    # Método extra para validar en la creación (llamado desde el ViewSet)
    @staticmethod
    def check_purchase(user, product_id):
        return OrderItem.objects.filter(
            order__user=user,
            order__status='PAGADO',  # O el estado que indique compra completada
            product_id=product_id
        ).exists()


class IsReviewAuthorOrReadOnly(permissions.BasePermission):
    """
    Permite editar/borrar solo al autor de la reseña.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user
