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
from apps.prestamos.services.usuarios import generar_username_unico


@transaction.atomic
def sincronizar_estudiante(data, password_inicial=None):
    """Crea o actualiza el espejo local de un estudiante.

    Args:
        data: dict con las claves de la API de matrículas (cedula, nombres,
              apellidos, correo, telefono, facultad, carrera, semestre, activo, id...).
        password_inicial: contraseña a fijar SOLO al crear el User por primera vez.
              Si es None, se usa la cédula (convención: clave inicial = cédula).

    Returns:
        (estudiante, creado): el Estudiante local y un bool de si el User es nuevo.

    La clave natural de cruce con la API es la CÉDULA. El username local sigue la
    convención institucional (inicial 1er nombre + 1er apellido + inicial 2º
    apellido). Idempotente: ejecutarla varias veces deja el mismo estado.
    """
    cedula = str(data['cedula']).strip()
    nombres = data.get('nombres', '')
    apellidos = data.get('apellidos', '')

    # 1) Catálogo: facultad y carrera
    facultad, _ = Facultad.objects.get_or_create(nombre=data['facultad'])
    carrera, _ = Carrera.objects.get_or_create(
        nombre=data['carrera'],
        defaults={'facultad': facultad},
    )

    # 2) Rol
    tipo_estudiante, _ = TipoUsuario.objects.get_or_create(nombre='Estudiante')

    # 3) auth.User. Se localiza por cédula (clave natural); el username sigue la
    #    convención institucional y solo se asigna al crear (estable después).
    perfil_existente = Usuario.objects.select_related('user').filter(cedula=cedula).first()

    if perfil_existente:
        user = perfil_existente.user
        user.first_name = nombres
        user.last_name = apellidos
        user.email = data.get('correo', '')
        user.is_active = bool(data.get('activo', True))
        user.save()
        user_creado = False
    else:
        username = generar_username_unico(nombres, apellidos)
        user = User.objects.create(
            username=username,
            first_name=nombres,
            last_name=apellidos,
            email=data.get('correo', ''),
            is_active=bool(data.get('activo', True)),
        )
        user.set_password(password_inicial or cedula)
        user.save()
        grupo_estudiante, _ = Group.objects.get_or_create(name='Estudiante')
        user.groups.add(grupo_estudiante)
        user_creado = True

    # 4) Perfil local (marca origen='api' para no pisar usuarios manuales)
    perfil, _ = Usuario.objects.update_or_create(
        user=user,
        defaults={
            'tipo_usuario': tipo_estudiante,
            'cedula': cedula,
            'telefono': str(data.get('telefono') or '')[:10],
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
