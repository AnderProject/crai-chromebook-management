from rest_framework import viewsets
from .models import EstudianteMatricula
from .serializers import EstudianteMatriculaSerializer


class EstudianteMatriculaViewSet(viewsets.ReadOnlyModelViewSet):
    """API de solo lectura de estudiantes matriculados.

    - GET /api/estudiantes/                 -> lista paginada (?search=cedula|apellidos|nombres)
    - GET /api/estudiantes/{cedula}/        -> detalle por cédula

    Por defecto solo expone estudiantes activos (activo=True). Para ver también
    inactivos, pasar ?incluir_inactivos=1.
    """

    serializer_class = EstudianteMatriculaSerializer
    lookup_field = 'cedula'
    search_fields = ['cedula', 'apellidos', 'nombres']

    def get_queryset(self):
        qs = EstudianteMatricula.objects.all()
        incluir_inactivos = self.request.query_params.get('incluir_inactivos')
        if not incluir_inactivos:
            qs = qs.filter(activo=True)
        return qs
