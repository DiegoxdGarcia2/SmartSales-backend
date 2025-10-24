from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    """
    Modelo para las categorías de productos.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    
    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Brand(models.Model):
    """
    Modelo para las marcas de productos.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    warranty_info = models.TextField(
        blank=True,
        null=True,
        verbose_name='Información de Garantía'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Modelo para los productos del sistema.
    """
    name = models.CharField(
        max_length=255,
        verbose_name='Nombre'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Precio'
    )
    stock = models.IntegerField(
        default=0,
        verbose_name='Stock'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Categoría'
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        related_name='products',
        null=True,
        blank=True,
        verbose_name='Marca'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class Review(models.Model):
    """
    Modelo para las reseñas de productos.
    """
    product = models.ForeignKey(
        Product,
        related_name='reviews',
        on_delete=models.CASCADE,
        verbose_name='Producto'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='reviews',
        on_delete=models.CASCADE,
        verbose_name='Usuario'
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Calificación (1-5)'
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name='Comentario'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )

    class Meta:
        verbose_name = 'Reseña'
        verbose_name_plural = 'Reseñas'
        # Evitar que un usuario deje más de una reseña por producto
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f'Reseña de {self.user.username} para {self.product.name} ({self.rating} estrellas)'
