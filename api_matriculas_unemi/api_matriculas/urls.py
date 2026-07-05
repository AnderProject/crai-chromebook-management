"""URLs raíz de la API de matrículas."""
from django.contrib import admin
from django.urls import path, include

from matriculas.views_web import panel_matriculas

urlpatterns = [
    # Interfaz web del simulador (registrar/gestionar estudiantes matriculados)
    path('', panel_matriculas, name='panel_matriculas'),
    path('admin/', admin.site.urls),
    path('api/', include('matriculas.urls')),
]
