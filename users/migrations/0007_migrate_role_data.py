# Generated manually on 2025-10-22 01:38

from django.db import migrations


def migrate_role_data(apps, schema_editor):
    """Migra los datos del campo role_old al nuevo campo role"""
    User = apps.get_model('users', 'User')
    Role = apps.get_model('users', 'Role')
    
    # Mapeo de roles antiguos a nuevos IDs
    role_mapping = {
        'ADMINISTRADOR': 1,
        'CLIENTE': 2,
    }
    
    for user in User.objects.all():
        if user.role_old:
            role_id = role_mapping.get(user.role_old, 2)  # Default a CLIENTE si no existe
            try:
                role = Role.objects.get(id=role_id)
                user.role = role
                user.save(update_fields=['role'])
            except Role.DoesNotExist:
                print(f"Advertencia: No se encontró el rol con ID {role_id} para el usuario {user.username}")


def reverse_migration(apps, schema_editor):
    """Revierte la migración copiando role de vuelta a role_old"""
    User = apps.get_model('users', 'User')
    
    for user in User.objects.all():
        if user.role:
            user.role_old = user.role.name
            user.save(update_fields=['role_old'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_add_new_role_field'),
    ]

    operations = [
        migrations.RunPython(migrate_role_data, reverse_migration),
    ]
