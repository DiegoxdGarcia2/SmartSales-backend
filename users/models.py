from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    """
    Modelo de Usuario personalizado para SmartSales365.
    Extiende AbstractUser para añadir roles personalizados.
    """
    ROLE_CHOICES = [
        ('ADMINISTRADOR', 'Administrador'),
        ('CLIENTE', 'Cliente'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='CLIENTE',
        verbose_name='Rol'
    )
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class ClientProfile(models.Model):
    """
    Perfil extendido para los clientes.
    Relación uno a uno con el modelo User.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_profile',
        verbose_name='Usuario'
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name='Nombre completo'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Número de teléfono'
    )
    address = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Dirección'
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
        verbose_name = 'Perfil de Cliente'
        verbose_name_plural = 'Perfiles de Clientes'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.user.username
