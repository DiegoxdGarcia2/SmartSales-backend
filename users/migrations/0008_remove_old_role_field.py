# Generated manually on 2025-10-22 01:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_migrate_role_data'),
    ]

    operations = [
        # Eliminar el campo role_old
        migrations.RemoveField(
            model_name='user',
            name='role_old',
        ),
    ]
