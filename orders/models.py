from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product
from decimal import Decimal

User = get_user_model()


class Cart(models.Model):
    """
    Carrito de compras - Cada usuario tiene un carrito único
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='Usuario'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última Actualización')

    class Meta:
        verbose_name = 'Carrito'
        verbose_name_plural = 'Carritos'

    def __str__(self):
        return f"Carrito de {self.user.username}"

    def get_total_price(self):
        """
        Calcula el precio total de todos los items en el carrito
        """
        total = sum(item.get_item_price() for item in self.items.all())
        return Decimal(str(total))


class CartItem(models.Model):
    """
    Item individual en el carrito
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Carrito'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Producto'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='Cantidad'
    )

    class Meta:
        verbose_name = 'Item de Carrito'
        verbose_name_plural = 'Items de Carrito'
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product'],
                name='unique_cart_product'
            )
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    def get_item_price(self):
        """
        Calcula el precio total del item (cantidad * precio unitario)
        """
        return Decimal(str(self.quantity)) * self.product.price


class Order(models.Model):
    """
    Orden de compra - Registro histórico de compras
    """
    STATUS_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PAGADO', 'Pagado'),
        ('ENVIADO', 'Enviado'),
        ('CANCELADO', 'Cancelado'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('fallido', 'Fallido'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Usuario'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado'
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Precio Total'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última Actualización')

    # Campos opcionales para dirección de envío (pueden usarse datos de ClientProfile)
    shipping_address = models.TextField(
        blank=True,
        null=True,
        verbose_name='Dirección de Envío'
    )
    shipping_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Teléfono de Contacto'
    )

    # Campos de Stripe para integración de pagos
    stripe_checkout_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Stripe Checkout Session ID'
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Stripe Payment Intent ID'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pendiente',
        verbose_name='Estado de Pago'
    )

    class Meta:
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'
        ordering = ['-created_at']

    def __str__(self):
        return f"Orden #{self.id} - {self.user.username}"


class OrderItem(models.Model):
    """
    Item individual de una orden
    Almacena el precio al momento de la compra para mantener historial
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Orden'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Producto'
    )
    quantity = models.PositiveIntegerField(verbose_name='Cantidad')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Precio Unitario'
    )

    class Meta:
        verbose_name = 'Item de Orden'
        verbose_name_plural = 'Items de Orden'

    def __str__(self):
        product_name = self.product.name if self.product else "Producto eliminado"
        return f"{self.quantity}x {product_name}"

    def get_item_price(self):
        """
        Calcula el precio total del item (cantidad * precio al momento de compra)
        """
        return Decimal(str(self.quantity)) * self.price
