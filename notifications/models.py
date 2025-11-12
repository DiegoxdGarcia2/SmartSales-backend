from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Notification(models.Model):
    """Notificaciones del usuario"""
    
    # Tipos principales de notificaciones
    TYPE_CHOICES = [
        # Pedidos
        ('ORDER_CONFIRMED', 'Pedido Confirmado'),
        ('ORDER_SHIPPED', 'Pedido Enviado'),
        ('ORDER_DELIVERED', 'Pedido Entregado'),
        
        # Pagos
        ('PAYMENT_SUCCESS', 'Pago Exitoso'),
        ('PAYMENT_FAILED', 'Pago Fallido'),
        
        # Ofertas
        ('NEW_OFFER', 'Nueva Oferta Disponible'),
        ('OFFER_EXPIRING', 'Oferta Por Vencer'),
        
        # Sistema
        ('STOCK_AVAILABLE', 'Producto Disponible'),
        ('SYSTEM_ALERT', 'Alerta del Sistema'),
    ]
    
    CHANNEL_CHOICES = [
        ('IN_APP', 'En la App'),
        ('PUSH', 'Push Notification'),
        ('EMAIL', 'Correo Electrónico'),
    ]
    
    # Campos básicos
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    
    # Contenido
    title = models.CharField(max_length=200)
    message = models.TextField()
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji o nombre de icon")
    
    # Datos adicionales (JSON para flexibilidad)
    data = models.JSONField(null=True, blank=True, help_text="Datos adicionales para la notificación")
    
    # Acción (link/botón)
    action_url = models.CharField(max_length=500, blank=True, null=True, help_text="URL de destino al hacer click")
    action_text = models.CharField(max_length=100, blank=True, null=True, default='Ver Detalles')
    
    # Estado
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['type']),
        ]
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_type_display()}"
    
    def mark_as_read(self):
        """Marcar notificación como leída"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(models.Model):
    """Preferencias de notificaciones del usuario"""
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='notification_preferences'
    )
    
    # Preferencias para Pedidos
    orders_in_app = models.BooleanField(default=True, verbose_name="Pedidos (In-App)")
    orders_push = models.BooleanField(default=True, verbose_name="Pedidos (Push)")
    orders_email = models.BooleanField(default=True, verbose_name="Pedidos (Email)")
    
    # Preferencias para Ofertas
    offers_in_app = models.BooleanField(default=True, verbose_name="Ofertas (In-App)")
    offers_push = models.BooleanField(default=True, verbose_name="Ofertas (Push)")
    offers_email = models.BooleanField(default=False, verbose_name="Ofertas (Email)")
    
    # Preferencias para Sistema
    system_in_app = models.BooleanField(default=True, verbose_name="Sistema (In-App)")
    system_push = models.BooleanField(default=False, verbose_name="Sistema (Push)")
    system_email = models.BooleanField(default=False, verbose_name="Sistema (Email)")
    
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Preferencia de Notificación'
        verbose_name_plural = 'Preferencias de Notificaciones'
    
    def __str__(self):
        return f"Preferencias de {self.user.username}"
    
    def get_preference_for_type(self, notification_type, channel):
        """
        Obtiene la preferencia para un tipo de notificación y canal específico
        
        Args:
            notification_type: 'ORDER_CONFIRMED', 'NEW_OFFER', etc.
            channel: 'IN_APP', 'PUSH', 'EMAIL' (mayúsculas como en CHANNEL_CHOICES)
        
        Returns:
            bool: True si está habilitado, False si no
        """
        # Mapeo de tipos a categorías
        type_mapping = {
            'ORDER_CONFIRMED': 'orders',
            'ORDER_SHIPPED': 'orders',
            'ORDER_DELIVERED': 'orders',
            'PAYMENT_SUCCESS': 'orders',
            'PAYMENT_FAILED': 'orders',
            'NEW_OFFER': 'offers',
            'OFFER_EXPIRING': 'offers',
            'STOCK_AVAILABLE': 'system',
            'SYSTEM_ALERT': 'system',
        }
        
        # Normalizar canal a minúsculas para el nombre del campo
        channel_lower = channel.lower()
        
        category = type_mapping.get(notification_type, 'system')
        field_name = f'{category}_{channel_lower}'
        
        return getattr(self, field_name, True)


class DeviceToken(models.Model):
    """Tokens FCM para push notifications"""
    
    DEVICE_TYPES = [
        ('ANDROID', 'Android'),
        ('IOS', 'iOS'),
        ('WEB', 'Web'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255, unique=True, help_text="Token FCM del dispositivo")
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, default='WEB')
    device_name = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Nombre descriptivo del dispositivo (ej: Chrome en Windows)"
    )
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
        verbose_name = 'Token de Dispositivo'
        verbose_name_plural = 'Tokens de Dispositivos'
    
    def __str__(self):
        return f"{self.user.username} - {self.device_type} ({self.token[:20]}...)"
