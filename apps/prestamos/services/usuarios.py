"""Generación del nombre de usuario institucional.

Convención (igual que la API de matrículas): inicial del primer nombre +
primer apellido completo + inicial del segundo apellido, en minúsculas y sin
tildes. Ej: 'Anderson Alexander' + 'Merchan Balcazar' -> 'amerchanb'.
"""
import unicodedata

from django.contrib.auth.models import User


def _solo_letras(texto):
    normalizado = unicodedata.normalize('NFKD', texto)
    sin_tildes = normalizado.encode('ascii', 'ignore').decode('ascii')
    return ''.join(c for c in sin_tildes.lower() if c.isalpha())


def generar_username(nombres, apellidos):
    """Devuelve el usuario base según la convención (sin garantizar unicidad)."""
    nombres_part = nombres.split()
    apellidos_part = apellidos.split()

    primer_nombre = _solo_letras(nombres_part[0]) if nombres_part else ''
    primer_apellido = _solo_letras(apellidos_part[0]) if apellidos_part else ''
    segundo_apellido = _solo_letras(apellidos_part[1]) if len(apellidos_part) > 1 else ''

    return f'{primer_nombre[:1]}{primer_apellido}{segundo_apellido[:1]}'


def generar_username_unico(nombres, apellidos, excluir_user_id=None):
    """Como generar_username pero añade sufijo numérico si ya existe el usuario.

    excluir_user_id: id de User a ignorar en la comprobación (para no chocar con
    el propio usuario al actualizarlo).
    """
    base = generar_username(nombres, apellidos) or 'usuario'
    candidato, n = base, 2
    while True:
        choca = User.objects.filter(username=candidato)
        if excluir_user_id is not None:
            choca = choca.exclude(pk=excluir_user_id)
        if not choca.exists():
            return candidato
        candidato = f'{base}{n}'
        n += 1
