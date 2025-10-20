from django.contrib.auth.models import AbstractUser
from django.db import models


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
