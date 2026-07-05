"""Utilidades compartidas para la API de matrículas."""
import random
import unicodedata


def _solo_letras(texto):
    """Minúsculas, sin tildes ni caracteres no alfabéticos."""
    normalizado = unicodedata.normalize('NFKD', texto)
    sin_tildes = normalizado.encode('ascii', 'ignore').decode('ascii')
    return ''.join(c for c in sin_tildes.lower() if c.isalpha())


def generar_usuario(nombres, apellidos):
    """Usuario institucional: inicial del 1er nombre + 1er apellido + inicial del 2º apellido.

    Ej: 'Anderson Alexander' + 'Merchan Balcazar' -> 'amerchanb'.
    Es la MISMA convención que usa el sistema de reservas al sincronizar.
    """
    nombres_part = nombres.split()
    apellidos_part = apellidos.split()

    primer_nombre = _solo_letras(nombres_part[0]) if nombres_part else ''
    primer_apellido = _solo_letras(apellidos_part[0]) if apellidos_part else ''
    segundo_apellido = _solo_letras(apellidos_part[1]) if len(apellidos_part) > 1 else ''

    return f'{primer_nombre[:1]}{primer_apellido}{segundo_apellido[:1]}'


def generar_telefono():
    """Celular ecuatoriano: 09 + 8 dígitos."""
    return '09' + ''.join(str(random.randint(0, 9)) for _ in range(8))


def generar_cedula_ecuatoriana():
    """Cédula ecuatoriana de 10 dígitos con dígito verificador válido."""
    provincia = random.randint(1, 24)
    digitos = [int(d) for d in f'{provincia:02d}']
    digitos.append(random.randint(0, 5))  # tercer dígito (persona natural)
    digitos += [random.randint(0, 9) for _ in range(6)]  # dígitos 4 al 9

    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0
    for d, c in zip(digitos, coeficientes):
        producto = d * c
        suma += producto - 9 if producto > 9 else producto
    verificador = (10 - (suma % 10)) % 10
    digitos.append(verificador)
    return ''.join(str(d) for d in digitos)
