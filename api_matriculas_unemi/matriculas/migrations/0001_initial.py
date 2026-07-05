from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='EstudianteMatricula',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cedula', models.CharField(db_index=True, max_length=10, unique=True, verbose_name='Cédula')),
                ('nombres', models.CharField(max_length=100, verbose_name='Nombres')),
                ('apellidos', models.CharField(max_length=100, verbose_name='Apellidos')),
                ('correo', models.EmailField(max_length=254, verbose_name='Correo institucional')),
                ('facultad', models.CharField(max_length=150, verbose_name='Facultad')),
                ('carrera', models.CharField(max_length=150, verbose_name='Carrera')),
                ('semestre', models.IntegerField(verbose_name='Semestre')),
                ('estado_matricula', models.CharField(choices=[('activo', 'Activo'), ('retirado', 'Retirado'), ('egresado', 'Egresado')], default='activo', max_length=20, verbose_name='Estado de Matrícula')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Estudiante Matriculado',
                'verbose_name_plural': 'Estudiantes Matriculados',
                'db_table': 'tb_estudiante_matricula',
                'ordering': ['apellidos', 'nombres'],
            },
        ),
    ]
