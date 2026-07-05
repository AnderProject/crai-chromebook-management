from django.conf import settings
from rest_framework.permissions import BasePermission


class TieneApiKey(BasePermission):
    """Permite el acceso solo si el header X-API-KEY coincide con la clave configurada.

    Autenticación simple por clave compartida entre la API de matrículas y el
    sistema de reservas. Suficiente para un entorno de tesis/demo.
    """

    message = 'Clave de API inválida o ausente (header X-API-KEY).'

    def has_permission(self, request, view):
        clave_recibida = request.headers.get('X-API-KEY')
        return bool(clave_recibida) and clave_recibida == settings.API_KEY_MATRICULAS
