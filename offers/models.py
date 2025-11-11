"""
Modelos para el sistema de ofertas de SmartSales.
Gestiona ofertas de productos con diferentes tipos y seguimiento de interacciones.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
from products.models import Product

User = get_user_model()


class Offer(models.Model):
    """
    Modelo principal de Ofertas.
    Representa una oferta que puede aplicarse a uno o varios productos.
    """
    
    OFFER_TYPES = [
        ('FLASH_SALE', 'Venta Flash'),           # Oferta por tiempo limitado (pocas horas)
        ('DAILY_DEAL', 'Oferta del Día'),        # Oferta diaria
        ('SEASONAL', 'Oferta de Temporada'),     # Navidad, Black Friday, etc.
        ('CLEARANCE', 'Liquidación'),            # Liquidar stock antiguo
        ('PERSONALIZED', 'Oferta Personalizada'), # Basada en ML para usuario específico
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Borrador'),
        ('ACTIVE', 'Activa'),
        ('PAUSED', 'Pausada'),
        ('EXPIRED', 'Expirada'),
        ('CANCELLED', 'Cancelada'),
    ]
    
    # Información básica
    name = models.CharField(max_length=200, help_text="Nombre descriptivo de la oferta")
    description = models.TextField(blank=True, help_text="Descripción detallada")
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPES)
    
    # Descuento
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Porcentaje de descuento (0-100)"
    )
    
    # Vigencia
    start_date = models.DateTimeField(help_text="Fecha y hora de inicio")
    end_date = models.DateTimeField(help_text="Fecha y hora de fin")
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Restricciones
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Número máximo de usos (null = ilimitado)"
    )
    max_uses_per_user = models.PositiveIntegerField(
        default=1,
        help_text="Usos máximos por usuario"
    )
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monto mínimo de compra requerido"
    )
    
    # Personalización (para ofertas ML)
    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='personalized_offers',
        help_text="Usuario específico para ofertas personalizadas"
    )
    
    # Prioridad (para mostrar primero ofertas más importantes)
    priority = models.IntegerField(
        default=0,
        help_text="Mayor prioridad = se muestra primero"
    )
    
    # Estadísticas
    views_count = models.PositiveIntegerField(default=0)
    clicks_count = models.PositiveIntegerField(default=0)
    conversions_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='offers_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status', 'start_date', 'end_date']),
            models.Index(fields=['offer_type', 'status']),
            models.Index(fields=['target_user', 'status']),
        ]
        verbose_name = 'Oferta'
        verbose_name_plural = 'Ofertas'
    
    def __str__(self):
        return f"{self.name} ({self.discount_percentage}% off)"
    
    def is_active(self):
        """Verifica si la oferta está activa y dentro del período de vigencia"""
        now = timezone.now()
        return (
            self.status == 'ACTIVE' and
            self.start_date <= now <= self.end_date and
            (self.max_uses is None or self.conversions_count < self.max_uses)
        )
    
    def is_valid_for_user(self, user):
        """Verifica si un usuario puede usar esta oferta"""
        if not self.is_active():
            return False
        
        # Si es oferta personalizada, solo el target_user puede usarla
        if self.target_user and self.target_user != user:
            return False
        
        # Verificar usos del usuario
        user_uses = UserOfferInteraction.objects.filter(
            offer=self,
            user=user,
            action='USED'
        ).count()
        
        return user_uses < self.max_uses_per_user
    
    def can_apply_to_cart(self, cart_total):
        """Verifica si la oferta puede aplicarse a un carrito con cierto total"""
        if not self.is_active():
            return False
        
        if self.min_purchase_amount and cart_total < self.min_purchase_amount:
            return False
        
        return True
    
    def calculate_discount(self, original_price):
        """Calcula el precio con descuento"""
        discount_amount = original_price * (self.discount_percentage / 100)
        return original_price - discount_amount
    
    def increment_view(self):
        """Incrementa el contador de vistas"""
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def increment_click(self):
        """Incrementa el contador de clicks"""
        self.clicks_count += 1
        self.save(update_fields=['clicks_count'])
    
    def increment_conversion(self):
        """Incrementa el contador de conversiones"""
        self.conversions_count += 1
        self.save(update_fields=['conversions_count'])
    
    def get_conversion_rate(self):
        """Calcula la tasa de conversión"""
        if self.clicks_count == 0:
            return 0
        return (self.conversions_count / self.clicks_count) * 100
    
    def time_remaining(self):
        """Retorna el tiempo restante de la oferta"""
        if not self.is_active():
            return None
        return self.end_date - timezone.now()
    
    def hours_remaining(self):
        """Retorna las horas restantes de la oferta"""
        remaining = self.time_remaining()
        if remaining is None:
            return 0
        return int(remaining.total_seconds() / 3600)


class OfferProduct(models.Model):
    """
    Relación muchos-a-muchos entre Ofertas y Productos.
    Permite que una oferta tenga múltiples productos y viceversa.
    """
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='offer_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_offers')
    
    # Permite override del descuento para este producto específico
    custom_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Descuento específico para este producto (override)"
    )
    
    # Orden de display
    display_order = models.PositiveIntegerField(default=0)
    
    # Timestamps
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_order', '-added_at']
        unique_together = ['offer', 'product']
        verbose_name = 'Producto en Oferta'
        verbose_name_plural = 'Productos en Oferta'
    
    def __str__(self):
        return f"{self.product.name} - {self.offer.name}"
    
    def get_discount_percentage(self):
        """Retorna el descuento aplicable (custom o del offer)"""
        return self.custom_discount if self.custom_discount else self.offer.discount_percentage
    
    def get_discounted_price(self):
        """Calcula el precio con descuento"""
        discount = self.get_discount_percentage()
        return self.product.price * (1 - discount / 100)
    
    def get_savings(self):
        """Calcula el ahorro en dinero"""
        return self.product.price - self.get_discounted_price()


class UserOfferInteraction(models.Model):
    """
    Registra las interacciones de usuarios con ofertas.
    Útil para analytics y ML.
    """
    
    ACTION_CHOICES = [
        ('VIEWED', 'Vista'),
        ('CLICKED', 'Click'),
        ('ADDED_TO_CART', 'Agregado al Carrito'),
        ('USED', 'Usada en Compra'),
        ('DISMISSED', 'Descartada'),
        ('EXPIRED', 'Expiró sin usar'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offer_interactions')
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='user_interactions')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Producto específico si aplica
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Metadata
    session_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'offer', 'action']),
            models.Index(fields=['offer', 'action', 'created_at']),
        ]
        verbose_name = 'Interacción de Usuario con Oferta'
        verbose_name_plural = 'Interacciones de Usuarios con Ofertas'
    
    def __str__(self):
        return f"{self.user.username} - {self.offer.name} - {self.action}"


class OfferRecommendation(models.Model):
    """
    Guarda las recomendaciones de ofertas generadas por ML.
    Permite tracking de efectividad del modelo.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offer_recommendations')
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='recommendations')
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Producto recomendado dentro de la oferta"
    )
    
    # Score del modelo ML (0-1)
    score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Probabilidad de conversión (0-1)"
    )
    
    # Razones de la recomendación
    reason = models.JSONField(
        default=dict,
        help_text="Factores que influyeron en la recomendación"
    )
    
    # Tracking
    was_shown = models.BooleanField(default=False)
    shown_at = models.DateTimeField(null=True, blank=True)
    was_clicked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)
    was_converted = models.BooleanField(default=False)
    converted_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    model_version = models.CharField(max_length=50, default='1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-score', '-created_at']
        indexes = [
            models.Index(fields=['user', 'score']),
            models.Index(fields=['was_converted', 'score']),
        ]
        verbose_name = 'Recomendación de Oferta'
        verbose_name_plural = 'Recomendaciones de Ofertas'
    
    def __str__(self):
        return f"{self.user.username} - {self.offer.name} (score: {self.score:.2f})"
    
    def mark_shown(self):
        """Marca la recomendación como mostrada"""
        if not self.was_shown:
            self.was_shown = True
            self.shown_at = timezone.now()
            self.save(update_fields=['was_shown', 'shown_at'])
    
    def mark_clicked(self):
        """Marca la recomendación como clickeada"""
        if not self.was_clicked:
            self.was_clicked = True
            self.clicked_at = timezone.now()
            self.save(update_fields=['was_clicked', 'clicked_at'])
    
    def mark_converted(self):
        """Marca la recomendación como convertida"""
        if not self.was_converted:
            self.was_converted = True
            self.converted_at = timezone.now()
            self.save(update_fields=['was_converted', 'converted_at'])
