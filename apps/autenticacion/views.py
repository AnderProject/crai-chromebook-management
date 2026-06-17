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

    sincronizar_estudiante(data, password_inicial=cedula)
    user = authenticate(username=cedula, password=contraseña)

    if user is None:
        # El estudiante existe pero la contraseña no coincide con la inicial.
        return None, 'Tu usuario y tu contraseña inicial son tu número de cédula.'

    return user, None


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

            user = autenticar_usuario(usuario_ingresado, contraseña)

            # Sync on-demand: estudiante que aún no existe localmente pero sí en matrículas.
            mensaje_sync = None
            if user is None and usuario_ingresado.isdigit() and len(usuario_ingresado) == 10:
                user, mensaje_sync = sincronizar_y_autenticar(usuario_ingresado, contraseña)

            if user is not None and user.is_active:
                grupos = [g.name for g in user.groups.all()]

                if 'Estudiante' in grupos or (not user.is_staff and not user.is_superuser):
                    login(request, user)
                    limpiar_mensajes(request)
                    messages.success(request, f'¡Bienvenido/a {user.first_name or user.username}! 🎓')
                    return redirect('estudiantes:portal_estudiante')
                else:
                    messages.error(request, 'Credenciales Incorrectas.')
            else:
                messages.error(request, mensaje_sync or 'Usuario o contraseña incorrectos.')
    
    contexto = {
        'formulario': formulario,
        'titulo_pagina': 'Login Estudiante - CRAI UNEMI'
    }
    return render(request, 'autenticacion/login_estudiante.html', contexto)


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
            
            user = autenticar_usuario(usuario_ingresado, contraseña)
            
            if user is not None and user.is_active:
                grupos = [g.name for g in user.groups.all()]
                
                if 'Administrador' in grupos or 'Recepcionista' in grupos or user.is_staff or user.is_superuser:
                    login(request, user)
                    limpiar_mensajes(request)
                    messages.success(request, f'¡Bienvenido/a {user.first_name or user.username}! 🛡️')
                    return redirect('prestamos:portal')
                else:
                    messages.error(request, 'Credenciales Incorrectas')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
    
    contexto = {
        'formulario': formulario,
        'titulo_pagina': 'Login Administrador - CRAI UNEMI'
    }
    return render(request, 'autenticacion/login_admin.html', contexto)


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
    """Vista para recuperar contraseña"""
    
    limpiar_mensajes(request)
    formulario = FormularioRecuperarContraseña()
    
    if request.method == 'POST':
        formulario = FormularioRecuperarContraseña(request.POST)
        if formulario.is_valid():
            email = formulario.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                enlace = f"http://{request.get_host()}/autenticacion/cambiar-contraseña/{uid}/{token}/"
                
                send_mail(
                    'Recuperación de Contraseña - CRAI UNEMI',
                    f'Para restablecer tu contraseña, haz clic aquí:\n\n{enlace}\n\nEste enlace expira en 5 minutos.',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, 'Se ha enviado un enlace de recuperación a tu correo.')
                return redirect('autenticacion:seleccionar_perfil')
            except User.DoesNotExist:
                messages.error(request, 'No existe una cuenta con ese correo electrónico.')
    
    return render(request, 'autenticacion/recuperar_contraseña.html', {'formulario': formulario})


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
                messages.success(request, 'Contraseña cambiada exitosamente. Ya puedes iniciar sesión.')
                return redirect('autenticacion:seleccionar_perfil')
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