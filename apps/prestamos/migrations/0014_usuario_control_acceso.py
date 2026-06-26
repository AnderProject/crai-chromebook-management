# Generated manually on 2026-06-25 (control de acceso: bloqueo + sesión única)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prestamos', '0013_chromebook_garantia'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='intentos_fallidos',
            field=models.IntegerField(default=0, verbose_name='Intentos de login fallidos'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='cuenta_bloqueada',
            field=models.BooleanField(default=False, verbose_name='Cuenta bloqueada'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='session_key',
            field=models.CharField(blank=True, max_length=40, null=True, verbose_name='Sesión activa actual'),
        ),
    ]
