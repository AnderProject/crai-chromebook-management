from django.db import models
from django.contrib.auth.models import User


class Chromebook(models.Model):
    """Inventario de Chromebooks"""
    
    ESTADOS = [
        ('disponible', 'Disponible'),
        ('prestado', 'Prestado'),
        ('mantenimiento', 'Mantenimiento'),
    ]
    
    CONDICIONES = [
        ('excelente', 'Excelente'),
        ('bueno', 'Bueno'),
        ('regular', 'Regular'),
        ('malo', 'Malo'),
    ]
    
    codigo = models.CharField(max_length=10, unique=True)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=100)
    serie = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='disponible')
    condicion = models.CharField(max_length=20, choices=CONDICIONES, default='bueno')
    fecha_adquisicion = models.DateField(null=True, blank=True)
    notas = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Chromebook'
        verbose_name_plural = 'Chromebooks'
        ordering = ['codigo']

    def __str__(self):
        return f'{self.codigo} - {self.marca} {self.modelo}'


class Prestamo(models.Model):
    """Registro de préstamos"""
    
    ESTADOS = [
        ('activo', 'Activo'),
        ('devuelto', 'Devuelto'),
        ('vencido', 'Vencido'),
    ]
    
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE)
    chromebook = models.ForeignKey(Chromebook, on_delete=models.CASCADE)
    fecha_prestamo = models.DateTimeField(auto_now_add=True)
    fecha_devolucion = models.DateTimeField()
    fecha_devuelto = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='activo')
    duracion_horas = models.IntegerField(default=4)
    notas = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Préstamo'
        verbose_name_plural = 'Préstamos'
        ordering = ['-fecha_prestamo']

    def __str__(self):
        return f'Préstamo #{self.id} - {self.estudiante.username}'