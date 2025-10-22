from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import ClientProfile, Role

User = get_user_model()


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para el modelo Role.
    """
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información del Rol', {
            'fields': ('name', 'description')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Configuración del panel de administración para el modelo User personalizado.
    """
    # Campos que se mostrarán en la lista de usuarios
    list_display = ['username', 'email', 'role', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['role', 'is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    # Configuración de los fieldsets para el formulario de edición
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Rol y Permisos', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Fechas Importantes', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    # Configuración de los fieldsets para la creación de usuario
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )
    
    # Campos de solo lectura
    readonly_fields = ['date_joined', 'last_login']


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para el perfil de clientes.
    """
    list_display = ['user', 'full_name', 'phone_number', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email', 'full_name', 'phone_number']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Información del Cliente', {
            'fields': ('full_name', 'phone_number', 'address')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
