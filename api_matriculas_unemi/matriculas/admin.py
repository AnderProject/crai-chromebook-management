from django.contrib import admin
from .models import EstudianteMatricula


@admin.register(EstudianteMatricula)
class EstudianteMatriculaAdmin(admin.ModelAdmin):
    list_display = ('cedula', 'apellidos', 'nombres', 'carrera', 'semestre',
                    'estado_matricula', 'activo')
    list_filter = ('estado_matricula', 'activo', 'facultad', 'carrera')
    search_fields = ('cedula', 'apellidos', 'nombres', 'correo')
    ordering = ('apellidos', 'nombres')
