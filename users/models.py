from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class Role(models.Model):
    """
    Modelo para los roles del sistema.
    Permite gestionar roles de forma dinámica.
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Nombre del rol'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
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
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Modelo de Usuario personalizado para SmartSales365.
    Extiende AbstractUser para añadir roles personalizados.
    """
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='users',
        verbose_name='Rol',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        role_name = self.role.name if self.role else 'Sin rol'
        return f"{self.username} ({role_name})"


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
