from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from .forms import FormularioLogin, FormularioRecuperarContraseña


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def limpiar_mensajes(request):
    """Elimina TODOS los mensajes almacenados"""
    storage = messages.get_messages(request)
    for _ in storage:
        pass
    if 'messages' in request.session:
        del request.session['messages']


def obtener_rol(user):
    """Devuelve el rol del usuario como string"""
    if user.is_superuser:
        return 'Administrador'
    grupos = [g.name for g in user.groups.all()]
    if 'Administrador' in grupos:
        return 'Administrador'
    elif 'Recepcionista' in grupos:
        return 'Recepcionista'
    elif 'Estudiante' in grupos:
        return 'Estudiante'
    return 'Estudiante'


def redireccionar_por_rol(user):
    """Redirige al portal correspondiente según el rol del usuario"""
    grupos = [g.name for g in user.groups.all()]
    
    if 'Administrador' in grupos or 'Recepcionista' in grupos or user.is_staff or user.is_superuser:
        return redirect('prestamos:portal')
    else:
        return redirect('estudiantes:portal_estudiante')


def autenticar_usuario(usuario_ingresado, contraseña):
    """Intenta autenticar por username o email. Retorna el user o None"""
    user = authenticate(username=usuario_ingresado, password=contraseña)
    
    if user is None:
        try:
            usuario_por_email = User.objects.get(email=usuario_ingresado)
            user = authenticate(username=usuario_por_email.username, password=contraseña)
        except User.DoesNotExist:
            user = None

    return user


def sincronizar_y_autenticar(cedula, contraseña):
    """Sync on-demand para estudiantes que solo existen en la API de matrículas.

    Devuelve (user, mensaje_error). Si la API trae al estudiante, lo crea/actualiza
    localmente y reintenta autenticar. mensaje_error explica el fallo cuando user es None.
    """
    from apps.prestamos.services.api_estudiantes import obtener_estudiante, ApiEstudiantesError
    from apps.prestamos.services.sincronizacion import sincronizar_estudiante

    try:
        data = obtener_estudiante(cedula)
    except ApiEstudiantesError:
        return None, 'El servicio de matrículas no está disponible en este momento. Intenta más tarde.'

    if data is None:
        return None, None  # no es estudiante; deja el mensaje genérico al llamador

    estudiante, _ = sincronizar_estudiante(data, password_inicial=cedula)
    # El username sigue la convención institucional (no es la cédula); se autentica con él.
    username = estudiante.usuario.user.username
    user = authenticate(username=username, password=contraseña)

    if user is None:
        # El estudiante existe pero la contraseña no coincide con la inicial.
        return None, 'Tu contraseña inicial es tu número de cédula.'

    return user, None


# ==========================================
# CONTROL DE ACCESO: BLOQUEO POR INTENTOS + SESIÓN ÚNICA
# ==========================================

INTENTOS_MAXIMOS = 3


def _resolver_user(identificador):
    """Devuelve el User por username, email o cédula (sin validar contraseña), o None.

    Se incluye la cédula porque los estudiantes pueden iniciar sesión con su número
    de cédula; así el bloqueo por intentos también aplica en ese caso.
    """
    try:
        return User.objects.get(username=identificador)
    except User.DoesNotExist:
        pass
    try:
        return User.objects.get(email=identificador)
    except User.DoesNotExist:
        pass
    from apps.prestamos.models import Usuario
    perfil = Usuario.objects.filter(cedula=identificador).select_related('user').first()
    return perfil.user if perfil else None


def _perfil_de(user):
    """Perfil (apps.prestamos.Usuario) asociado al User, o None si no tiene."""
    return getattr(user, 'perfil', None) if user else None


def _cuenta_bloqueada(user):
    perfil = _perfil_de(user)
    return bool(perfil and perfil.cuenta_bloqueada)


def _registrar_intento_fallido(user):
    """Suma un intento fallido; bloquea al alcanzar el máximo.

    Devuelve (bloqueada: bool, restantes: int|None). restantes es None cuando el
    usuario no tiene perfil donde contabilizar (p. ej. superusuario sin perfil).
    """
    perfil = _perfil_de(user)
    if perfil is None:
        return False, None
    perfil.intentos_fallidos += 1
    if perfil.intentos_fallidos >= INTENTOS_MAXIMOS:
        perfil.cuenta_bloqueada = True
        perfil.save(update_fields=['intentos_fallidos', 'cuenta_bloqueada'])
        return True, 0
    perfil.save(update_fields=['intentos_fallidos'])
    return False, INTENTOS_MAXIMOS - perfil.intentos_fallidos


def _resetear_intentos(user):
    """Limpia el contador de intentos tras un login exitoso."""
    perfil = _perfil_de(user)
    if perfil is not None and (perfil.intentos_fallidos or perfil.cuenta_bloqueada):
        perfil.intentos_fallidos = 0
        perfil.cuenta_bloqueada = False
        perfil.save(update_fields=['intentos_fallidos', 'cuenta_bloqueada'])


def _activar_sesion_unica(request, user):
    """Registra la sesión actual como la única válida del usuario.

    Cualquier sesión anterior queda invalidada porque su session_key dejará de
    coincidir con la guardada (ver SesionUnicaMiddleware).
    """
    perfil = _perfil_de(user)
    if perfil is not None:
        perfil.session_key = request.session.session_key
        perfil.save(update_fields=['session_key'])


def _mensaje_intentos(request, bloqueada, restantes):
    """Mensaje de error coherente según el estado del bloqueo."""
    if bloqueada:
        messages.error(
            request,
            'Tu cuenta ha sido bloqueada por 3 intentos fallidos. '
            'Desbloquéala desde "¿Olvidó su contraseña?" eligiendo la opción '
            '"Cuenta bloqueada" e ingresando tu número de cédula.'
        )
    elif restantes is not None:
        plural = 'intento' if restantes == 1 else 'intentos'
        messages.error(request, f'Usuario o contraseña incorrectos. Te quedan {restantes} {plural}.')
    else:
        messages.error(request, 'Usuario o contraseña incorrectos.')


# ==========================================
# SELECTOR DE PERFIL (Página inicial)
# ==========================================

def seleccionar_perfil(request):
    """Página inicial: elegir entre Estudiante o Administrador"""
    
    if request.user.is_authenticated:
        return redireccionar_por_rol(request.user)
    
    limpiar_mensajes(request)
    
    return render(request, 'autenticacion/seleccionar_perfil.html')


# ==========================================
# LOGIN DE ESTUDIANTE
# ==========================================

def login_estudiante(request):
    """Login exclusivo para estudiantes"""
    
    if request.user.is_authenticated:
        return redirect('estudiantes:portal_estudiante')
    
    limpiar_mensajes(request)
    formulario = FormularioLogin()
    
    if request.method == 'POST':
        formulario = FormularioLogin(request.POST)
        
        if formulario.is_valid():
            usuario_ingresado = formulario.cleaned_data['usuario']
            contraseña = formulario.cleaned_data['contraseña']

            user_existente = _resolver_user(usuario_ingresado)

            if _cuenta_bloqueada(user_existente):
                messages.error(
                    request,
                    'Tu cuenta está bloqueada por 3 intentos fallidos. '
                    'Desbloquéala desde "¿Olvidaste tu contraseña?" usando tu número de cédula.'
                )
            else:
                user = autenticar_usuario(usuario_ingresado, contraseña)

                # Sync on-demand: estudiante que aún no existe localmente pero sí en matrículas.
                mensaje_sync = None
                if user is None and usuario_ingresado.isdigit() and len(usuario_ingresado) == 10:
                    user, mensaje_sync = sincronizar_y_autenticar(usuario_ingresado, contraseña)

                if user is not None and user.is_active:
                    grupos = [g.name for g in user.groups.all()]

                    if 'Estudiante' in grupos or (not user.is_staff and not user.is_superuser):
                        _resetear_intentos(user)
                        login(request, user)
                        _activar_sesion_unica(request, user)
                        limpiar_mensajes(request)
                        messages.success(request, f'¡Bienvenido/a {user.first_name or user.username}!')
                        return redirect('estudiantes:portal_estudiante')
                    else:
                        messages.error(request, 'Credenciales Incorrectas.')
                elif mensaje_sync:
                    # El estudiante existe en matrículas pero la contraseña no coincide:
                    # no contabilizamos intento local (aún puede no tener perfil local).
                    messages.error(request, mensaje_sync)
                else:
                    bloqueada, restantes = _registrar_intento_fallido(user_existente)
                    _mensaje_intentos(request, bloqueada, restantes)
    
    # En error/GET se vuelve al MISMO selector con la vista de estudiante abierta
    # y el mensaje de error visible ahí mismo (no se redirige a otra página).
    contexto = {
        'formulario': formulario,
        'abrir_vista': 'estudiante',
        'vista_error': 'estudiante',
        'titulo_pagina': 'Login Estudiante - CRAI UNEMI'
    }
    return render(request, 'autenticacion/seleccionar_perfil.html', contexto)


# ==========================================
# LOGIN DE ADMINISTRADOR
# ==========================================

def login_administrador(request):
    """Login exclusivo para administradores/recepcionistas"""
    
    if request.user.is_authenticated:
        return redirect('prestamos:portal')
    
    limpiar_mensajes(request)
    formulario = FormularioLogin()
    
    if request.method == 'POST':
        formulario = FormularioLogin(request.POST)
        
        if formulario.is_valid():
            usuario_ingresado = formulario.cleaned_data['usuario']
            contraseña = formulario.cleaned_data['contraseña']
            
            user_existente = _resolver_user(usuario_ingresado)

            if _cuenta_bloqueada(user_existente):
                messages.error(
                    request,
                    'Tu cuenta está bloqueada por 3 intentos fallidos. '
                    'Desbloquéala desde "¿Olvidó su contraseña?" usando tu número de cédula.'
                )
            else:
                user = autenticar_usuario(usuario_ingresado, contraseña)

                if user is not None and user.is_active:
                    grupos = [g.name for g in user.groups.all()]

                    if 'Administrador' in grupos or user.is_staff or user.is_superuser:
                        _resetear_intentos(user)
                        login(request, user)
                        _activar_sesion_unica(request, user)
                        limpiar_mensajes(request)
                        messages.success(request, f'¡Bienvenido/a {user.first_name or user.username}!')
                        return redirect('prestamos:portal')
                    else:
                        messages.error(request, 'Credenciales Incorrectas')
                else:
                    # Solo contar intentos si el usuario identificado tiene rol de administrador;
                    # evita que errores en el panel de admin bloqueen cuentas de otro rol.
                    grupos_existente = [g.name for g in user_existente.groups.all()] if user_existente else []
                    es_admin = (
                        'Administrador' in grupos_existente
                        or (user_existente and (user_existente.is_staff or user_existente.is_superuser))
                    )
                    if es_admin:
                        bloqueada, restantes = _registrar_intento_fallido(user_existente)
                        _mensaje_intentos(request, bloqueada, restantes)
                    else:
                        messages.error(request, 'Usuario o contraseña incorrectos.')

    contexto = {
        'formulario': formulario,
        'abrir_vista': 'administrador',
        'vista_error': 'administrador',
        'titulo_pagina': 'Login Administrador - CRAI UNEMI'
    }
    return render(request, 'autenticacion/seleccionar_perfil.html', contexto)


# ==========================================
# LOGIN DE RECEPCIONISTA
# ==========================================

def login_recepcionista(request):
    """Login exclusivo para recepcionistas (separado del de administrador)."""

    if request.user.is_authenticated:
        return redirect('prestamos:portal')

    limpiar_mensajes(request)
    formulario = FormularioLogin()

    if request.method == 'POST':
        formulario = FormularioLogin(request.POST)

        if formulario.is_valid():
            usuario_ingresado = formulario.cleaned_data['usuario']
            contraseña = formulario.cleaned_data['contraseña']

            user_existente = _resolver_user(usuario_ingresado)

            if _cuenta_bloqueada(user_existente):
                messages.error(
                    request,
                    'Tu cuenta está bloqueada por 3 intentos fallidos. '
                    'Desbloquéala desde "¿Olvidaste tu contraseña?" usando tu número de cédula.'
                )
            else:
                user = autenticar_usuario(usuario_ingresado, contraseña)

                if user is not None and user.is_active:
                    grupos = [g.name for g in user.groups.all()]

                    if 'Recepcionista' in grupos:
                        _resetear_intentos(user)
                        login(request, user)
                        _activar_sesion_unica(request, user)
                        limpiar_mensajes(request)
                        messages.success(request, f'¡Bienvenido/a {user.first_name or user.username}!')
                        return redirect('prestamos:portal')
                    else:
                        messages.error(request, 'Credenciales Incorrectas')
                else:
                    # Solo contar intentos si el usuario identificado tiene rol de recepcionista;
                    # evita bloquear cuentas de otro rol desde este panel.
                    grupos_existente = [g.name for g in user_existente.groups.all()] if user_existente else []
                    if 'Recepcionista' in grupos_existente:
                        bloqueada, restantes = _registrar_intento_fallido(user_existente)
                        _mensaje_intentos(request, bloqueada, restantes)
                    else:
                        messages.error(request, 'Usuario o contraseña incorrectos.')

    contexto = {
        'formulario': formulario,
        'abrir_vista': 'recepcionista',
        'vista_error': 'recepcionista',
        'titulo_pagina': 'Login Recepcionista - CRAI UNEMI'
    }
    return render(request, 'autenticacion/seleccionar_perfil.html', contexto)


# ==========================================
# LOGIN GENÉRICO (Redirige al selector)
# ==========================================

def pagina_login(request):
    """Login genérico - Redirige al selector de perfil"""
    return redirect('autenticacion:seleccionar_perfil')


# ==========================================
# RECUPERACIÓN DE CONTRASEÑA
# ==========================================

def recuperar_contraseña(request):
    """Recuperación de contraseña con dos modos:

    - NORMAL: el usuario ingresa su CORREO registrado (lo habitual).
    - CUENTA BLOQUEADA: cuando la cuenta se bloqueó por intentos fallidos, se
      pide la CÉDULA (dato que el usuario conoce con certeza y que además
      desbloquea la cuenta al completar el cambio de contraseña).
    El modo se elige con el interruptor de la página (o llegando con ?bloqueo=1).
    """
    import re as _re
    from apps.prestamos.models import Usuario

    limpiar_mensajes(request)

    # Modo inicial: por parámetro (?bloqueo=1) o el enviado en el POST.
    modo_bloqueo = request.GET.get('bloqueo') == '1'

    if request.method == 'POST':
        modo_bloqueo = request.POST.get('modo') == 'bloqueo'
        identificador = (request.POST.get('identificador') or '').strip()
        user = None

        if modo_bloqueo:
            # --- Cuenta bloqueada: se identifica por CÉDULA ---
            if not (identificador.isdigit() and len(identificador) == 10):
                messages.error(request, 'La cédula debe tener 10 dígitos.')
            else:
                perfil = Usuario.objects.filter(cedula=identificador).select_related('user').first()
                if perfil is None:
                    messages.error(request, 'No existe ninguna cuenta con ese número de cédula.')
                elif not perfil.user.email:
                    messages.error(request, 'Tu cuenta no tiene un correo registrado. Contacta al administrador.')
                else:
                    user = perfil.user
        else:
            # --- Caso normal: se identifica por CORREO ---
            if not _re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', identificador):
                messages.error(request, 'Ingresa un correo electrónico válido.')
            else:
                user = User.objects.filter(email__iexact=identificador, is_active=True).first()
                if user is None:
                    messages.error(request, 'No existe ninguna cuenta con ese correo electrónico.')

        if user is not None:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            enlace = f"http://{request.get_host()}/autenticacion/cambiar-contraseña/{uid}/{token}/"

            nombre = user.first_name.split()[0] if user.first_name else user.username
            texto_plano = (
                f'Hola {nombre}:\n\n'
                f'Recibimos una solicitud para restablecer la contraseña de tu cuenta del '
                f'CRAI de la UNEMI. Para crear una nueva contraseña (y desbloquear tu cuenta '
                f'si estaba bloqueada), abre este enlace:\n\n{enlace}\n\n'
                f'Por tu seguridad, el enlace caduca en 5 minutos y solo puede usarse una vez.\n\n'
                f'Si tú no solicitaste este cambio, ignora este correo: tu contraseña seguirá '
                f'siendo la misma.\n\n'
                f'— Centro de Recursos para el Aprendizaje y la Investigación (CRAI) · UNEMI'
            )

            send_mail(
                'Restablece tu contraseña · CRAI UNEMI',
                texto_plano,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
                html_message=_html_correo_recuperacion(nombre, enlace),
            )
            return render(request, 'autenticacion/recuperar_contraseña.html', {
                'enviado': True,
                'correo_enmascarado': _enmascarar_correo(user.email),
            })

    return render(request, 'autenticacion/recuperar_contraseña.html', {
        'modo_bloqueo': modo_bloqueo,
    })


def _enmascarar_correo(correo):
    """Devuelve el correo parcialmente oculto, p.ej. an***@gmail.com."""
    try:
        usuario, dominio = correo.split('@', 1)
    except ValueError:
        return correo
    visible = usuario[:2] if len(usuario) > 2 else usuario[:1]
    return f'{visible}***@{dominio}'


def _html_correo_recuperacion(nombre, enlace):
    """Cuerpo HTML del correo de recuperación con la identidad de la UNEMI/CRAI.

    Todo el estilo va en línea y sin imágenes externas (los clientes de correo
    las bloquean); la marca 'UNEMI' se muestra como texto, lo que se ve
    profesional y llega igual en Gmail, Outlook, etc.
    """
    return f"""\
<!DOCTYPE html>
<html lang="es">
<body style="margin:0;padding:0;background:#eef2f8;font-family:'Segoe UI',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2f8;padding:28px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="max-width:560px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(13,44,84,0.12);">
        <!-- Encabezado -->
        <tr>
          <td style="background:linear-gradient(120deg,#0d2c54,#14417b 70%,#1b5aa8);padding:30px 34px;">
            <div style="font-size:26px;font-weight:800;color:#ffffff;letter-spacing:3px;">UNEMI</div>
            <div style="font-size:13px;color:#f2a900;font-weight:600;margin-top:4px;letter-spacing:.4px;">
              CRAI · Centro de Recursos para el Aprendizaje
            </div>
          </td>
        </tr>
        <!-- Cuerpo -->
        <tr>
          <td style="padding:34px;">
            <h1 style="margin:0 0 6px;font-size:20px;color:#0d2c54;">Restablece tu contraseña</h1>
            <p style="margin:0 0 18px;font-size:15px;color:#3a4658;line-height:1.55;">
              Hola <strong>{nombre}</strong>, recibimos una solicitud para restablecer la
              contraseña de tu cuenta del CRAI. Haz clic en el botón para crear una nueva
              (y desbloquear tu cuenta si estaba bloqueada).
            </p>
            <table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0;">
              <tr><td align="center" style="border-radius:12px;background:linear-gradient(120deg,#14417b,#1b5aa8);">
                <a href="{enlace}" target="_blank"
                   style="display:inline-block;padding:14px 34px;color:#ffffff;font-size:15px;font-weight:700;
                          text-decoration:none;border-radius:12px;">
                  Restablecer contraseña
                </a>
              </td></tr>
            </table>
            <div style="background:#fff6e6;border:1px solid #ffe2a3;border-radius:10px;padding:12px 14px;margin:6px 0 18px;">
              <p style="margin:0;font-size:13px;color:#9a6700;">
                ⏱️ Por seguridad, este enlace <strong>caduca en 5 minutos</strong> y solo puede usarse una vez.
              </p>
            </div>
            <p style="margin:0 0 6px;font-size:13px;color:#7b8794;line-height:1.5;">
              Si el botón no funciona, copia y pega este enlace en tu navegador:
            </p>
            <p style="margin:0 0 18px;font-size:12px;color:#14417b;word-break:break-all;">{enlace}</p>
            <p style="margin:0;font-size:13px;color:#7b8794;line-height:1.5;">
              Si tú no solicitaste este cambio, ignora este correo: tu contraseña seguirá siendo la misma.
            </p>
          </td>
        </tr>
        <!-- Pie -->
        <tr>
          <td style="background:#f4f7fb;padding:18px 34px;border-top:1px solid #e3eaf4;">
            <p style="margin:0;font-size:12px;color:#9aa5b1;line-height:1.5;">
              Universidad Estatal de Milagro · CRAI<br>
              Este es un correo automático, por favor no respondas a este mensaje.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ==========================================
# CAMBIAR CONTRASEÑA
# ==========================================

def cambiar_contraseña(request, uidb64, token):
    """Vista para cambiar contraseña con enlace de recuperación"""
    
    limpiar_mensajes(request)
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            nueva = request.POST.get('nueva_contraseña')
            confirmar = request.POST.get('confirmar_contraseña')
            
            if nueva == confirmar and len(nueva) >= 8:
                user.set_password(nueva)
                user.save()

                # Desbloquear la cuenta: cambiar la contraseña limpia los intentos
                # fallidos y la bandera de bloqueo (también libera la sesión previa).
                perfil = getattr(user, 'perfil', None)
                if perfil is not None:
                    perfil.intentos_fallidos = 0
                    perfil.cuenta_bloqueada = False
                    perfil.session_key = None
                    perfil.save(update_fields=['intentos_fallidos', 'cuenta_bloqueada', 'session_key'])

                return render(request, 'autenticacion/cambiar_contraseña.html', {
                    'cambio_exitoso': True,
                })
            else:
                messages.error(request, 'Las contraseñas no coinciden o son muy cortas (mínimo 8 caracteres).')
        
        return render(request, 'autenticacion/cambiar_contraseña.html')
    else:
        messages.error(request, 'El enlace de recuperación es inválido o ha expirado.')
        return redirect('autenticacion:seleccionar_perfil')


# ==========================================
# CERRAR SESIÓN
# ==========================================

def cerrar_sesion(request):
    """Cerrar sesión del usuario"""
    limpiar_mensajes(request)
    logout(request)
    request.session.flush()
    return redirect('autenticacion:seleccionar_perfil')


# ==========================================
# SOPORTE TÉCNICO
# ==========================================

def soporte(request):
    """Página de soporte técnico"""
    return render(request, 'autenticacion/soporte.html', {'titulo_pagina': 'Soporte Técnico - CRAI UNEMI'})


def desarrolladores(request):
    """Página dedicada al equipo de desarrollo del sistema."""
    return render(request, 'autenticacion/desarrolladores.html', {'titulo_pagina': 'Desarrolladores - CRAI UNEMI'})