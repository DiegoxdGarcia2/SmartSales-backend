from django.db import models


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
    marca = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Marca'
    )
    garantia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Garantía',
        help_text='Ejemplo: 1 año, 6 meses, etc.'
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
