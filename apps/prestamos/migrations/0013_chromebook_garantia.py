# Generated manually on 2026-06-25 (garantía en inventario)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prestamos', '0012_configuracionsistema'),
    ]

    operations = [
        migrations.AddField(
            model_name='chromebook',
            name='tiene_garantia',
            field=models.BooleanField(default=False, verbose_name='¿Tiene garantía?'),
        ),
        migrations.AddField(
            model_name='chromebook',
            name='fecha_fin_garantia',
            field=models.DateField(blank=True, null=True, verbose_name='Garantía válida hasta'),
        ),
        migrations.AlterField(
            model_name='chromebook',
            name='fecha_adquisicion',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de compra/adquisición'),
        ),
    ]
