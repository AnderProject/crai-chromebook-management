"""
Cliente HTTP de la API externa de matrículas (la fuente de verdad de estudiantes).

Distingue dos situaciones que los llamadores deben tratar distinto:
  - El estudiante NO existe en matrículas        -> devuelve None (HTTP 404).
  - La API está caída / lenta / responde 5xx      -> lanza ApiEstudiantesError.

Así una vista puede decidir: "no es estudiante" (mensaje claro) vs "servicio no
disponible" (fallback a la copia local).
"""
import requests
from django.conf import settings


class ApiEstudiantesError(Exception):
    """La API de matrículas no está disponible o respondió con error."""


def _headers():
    return {'X-API-KEY': settings.API_MATRICULAS_KEY}


def _base_url():
    return settings.API_MATRICULAS_BASE_URL.rstrip('/')


def obtener_estudiante(cedula):
    """Devuelve el dict del estudiante por cédula, o None si no existe (404).

    Lanza ApiEstudiantesError si la API está caída o responde con error.
    """
    url = f'{_base_url()}/estudiantes/{cedula}/'
    try:
        resp = requests.get(url, headers=_headers(), timeout=settings.API_MATRICULAS_TIMEOUT)
    except requests.RequestException as exc:
        raise ApiEstudiantesError(f'No se pudo contactar la API de matrículas: {exc}')

    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise ApiEstudiantesError(f'La API de matrículas respondió HTTP {resp.status_code}.')

    try:
        return resp.json()
    except ValueError as exc:
        raise ApiEstudiantesError(f'Respuesta inválida de la API de matrículas: {exc}')


def listar_estudiantes(search=None):
    """Itera TODOS los estudiantes siguiendo la paginación de DRF (campo 'next').

    Devuelve una lista de dicts. Lanza ApiEstudiantesError si la API falla.
    Usado por el comando de sincronización masiva y por la búsqueda por nombre.
    """
    url = f'{_base_url()}/estudiantes/'
    params = {'search': search} if search else None
    resultados = []

    while url:
        try:
            resp = requests.get(url, headers=_headers(), params=params,
                                timeout=settings.API_MATRICULAS_TIMEOUT)
        except requests.RequestException as exc:
            raise ApiEstudiantesError(f'No se pudo contactar la API de matrículas: {exc}')

        if resp.status_code != 200:
            raise ApiEstudiantesError(f'La API de matrículas respondió HTTP {resp.status_code}.')

        data = resp.json()
        # DRF paginado: {'count','next','previous','results':[...]}. Sin paginar: lista.
        if isinstance(data, dict) and 'results' in data:
            resultados.extend(data['results'])
            url = data.get('next')
            params = None  # 'next' ya incluye los parámetros
        else:
            resultados.extend(data)
            url = None

    return resultados
