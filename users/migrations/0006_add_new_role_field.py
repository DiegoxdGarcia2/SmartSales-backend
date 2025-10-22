# Generated manually on 2025-10-22 01:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_rename_old_role'),
    ]

    operations = [
        # Agregar el nuevo campo role como ForeignKey
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='users',
                to='users.role',
                verbose_name='Rol'
            ),
        ),
    ]
