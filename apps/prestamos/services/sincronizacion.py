"""
Sincronización espejo: convierte un estudiante de la API de matrículas en la
cadena completa de objetos locales que el sistema de reservas necesita.

    Facultad -> Carrera -> auth.User -> Usuario (perfil) -> Estudiante

Es la ÚNICA función que crea/actualiza estudiantes a partir de la API; todos los
puntos de integración (login, reservar, buscar, ficha) la reutilizan.
"""
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.utils import timezone

from apps.prestamos.models import (
    Facultad, Carrera, TipoUsuario, Usuario, Estudiante,
)


@transaction.atomic
def sincronizar_estudiante(data, password_inicial=None):
    """Crea o actualiza el espejo local de un estudiante.

    Args:
        data: dict con las claves de la API de matrículas (cedula, nombres,
              apellidos, correo, facultad, carrera, semestre, activo, id...).
        password_inicial: contraseña a fijar SOLO al crear el User por primera vez.
              Si es None, se usa la cédula (convención: usuario y clave = cédula).

    Returns:
        (estudiante, creado): el Estudiante local y un bool de si el User es nuevo.

    Idempotente: ejecutarla varias veces deja el mismo estado y refleja los
    cambios de la API (cambio de carrera, semestre, etc.).
    """
    cedula = str(data['cedula']).strip()

    # 1) Catálogo: facultad y carrera
    facultad, _ = Facultad.objects.get_or_create(nombre=data['facultad'])
    carrera, _ = Carrera.objects.get_or_create(
        nombre=data['carrera'],
        defaults={'facultad': facultad},
    )

    # 2) Rol
    tipo_estudiante, _ = TipoUsuario.objects.get_or_create(nombre='Estudiante')

    # 3) auth.User (username = cédula, clave estable y única)
    user, user_creado = User.objects.update_or_create(
        username=cedula,
        defaults={
            'first_name': data.get('nombres', ''),
            'last_name': data.get('apellidos', ''),
            'email': data.get('correo', ''),
            'is_active': bool(data.get('activo', True)),
        },
    )
    if user_creado:
        user.set_password(password_inicial or cedula)
        user.save()
        grupo_estudiante, _ = Group.objects.get_or_create(name='Estudiante')
        user.groups.add(grupo_estudiante)

    # 4) Perfil local (marca origen='api' para no pisar usuarios manuales)
    perfil, _ = Usuario.objects.update_or_create(
        user=user,
        defaults={
            'tipo_usuario': tipo_estudiante,
            'cedula': cedula,
            'origen': 'api',
            'matricula_id': data.get('id'),
            'sincronizado': timezone.now(),
        },
    )

    # 5) Estudiante
    estudiante, _ = Estudiante.objects.update_or_create(
        usuario=perfil,
        defaults={
            'carrera': carrera,
            'semestre': data.get('semestre', 1),
        },
    )

    return estudiante, user_creado
