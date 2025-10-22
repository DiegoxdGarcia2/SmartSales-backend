# Generated manually on 2025-10-22 01:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_populate_roles'),
    ]

    operations = [
        # Renombrar el campo role antiguo
        migrations.RenameField(
            model_name='user',
            old_name='role',
            new_name='role_old',
        ),
    ]
