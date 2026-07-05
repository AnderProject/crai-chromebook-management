from rest_framework import serializers
from .models import EstudianteMatricula


class EstudianteMatriculaSerializer(serializers.ModelSerializer):
    """Contrato JSON que consume el sistema de reservas.

    Las claves de aquí son las que espera `sincronizar_estudiante` en proyecto_crai.
    """

    class Meta:
        model = EstudianteMatricula
        fields = [
            'id',
            'cedula',
            'nombres',
            'apellidos',
            'correo',
            'telefono',
            'facultad',
            'carrera',
            'semestre',
            'estado_matricula',
            'activo',
            'creado',
            'actualizado',
        ]
