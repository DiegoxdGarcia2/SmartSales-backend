# Generated manually on 2025-10-22 01:35

from django.db import migrations


def create_initial_roles(apps, schema_editor):
    """Crea los roles iniciales ADMINISTRADOR y CLIENTE"""
    Role = apps.get_model('users', 'Role')
    
    Role.objects.create(
        id=1,
        name='ADMINISTRADOR',
        description='Administrador del sistema con acceso completo a todas las funcionalidades'
    )
    
    Role.objects.create(
        id=2,
        name='CLIENTE',
        description='Cliente del sistema con permisos para realizar compras y gestionar su perfil'
    )


def reverse_roles(apps, schema_editor):
    """Elimina los roles creados"""
    Role = apps.get_model('users', 'Role')
    Role.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_create_role_model'),
    ]

    operations = [
        migrations.RunPython(create_initial_roles, reverse_roles),
    ]
