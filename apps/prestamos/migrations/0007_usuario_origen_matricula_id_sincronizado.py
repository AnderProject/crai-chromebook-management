from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prestamos', '0006_chromebook_foto_alter_chromebook_condicion'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='origen',
            field=models.CharField(choices=[('local', 'Local'), ('api', 'API Matrículas')], default='local', max_length=10, verbose_name='Origen'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='matricula_id',
            field=models.IntegerField(blank=True, db_index=True, null=True, verbose_name='ID en Matrículas'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='sincronizado',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Última sincronización'),
        ),
    ]
