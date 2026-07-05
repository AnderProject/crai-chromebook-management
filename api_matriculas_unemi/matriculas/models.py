from django.db import models


class EstudianteMatricula(models.Model):
    """
    Estudiante tal como existe en el sistema de matrículas de la UNEMI.

    Esta es la *fuente de verdad*. El sistema de reservas (proyecto_crai) consume
    estos datos vía API y mantiene un espejo local. La `cedula` es la clave natural
    de cruce entre ambos sistemas.
    """

    ESTADOS_MATRICULA = [
        ('activo', 'Activo'),
        ('retirado', 'Retirado'),
        ('egresado', 'Egresado'),
    ]

    cedula = models.CharField(max_length=10, unique=True, db_index=True, verbose_name='Cédula')
    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    correo = models.EmailField(verbose_name='Correo institucional')
    telefono = models.CharField(max_length=10, blank=True, default='', verbose_name='Teléfono')
    facultad = models.CharField(max_length=150, verbose_name='Facultad')
    carrera = models.CharField(max_length=150, verbose_name='Carrera')
    semestre = models.IntegerField(verbose_name='Semestre')
    estado_matricula = models.CharField(
        max_length=20, choices=ESTADOS_MATRICULA, default='activo',
        verbose_name='Estado de Matrícula',
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tb_estudiante_matricula'
        verbose_name = 'Estudiante Matriculado'
        verbose_name_plural = 'Estudiantes Matriculados'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f'{self.cedula} - {self.apellidos} {self.nombres}'
