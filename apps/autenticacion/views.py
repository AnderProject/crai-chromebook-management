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
# SELECTOR DE PERFIL (Página inicial)
# ==========================================
def seleccionar_perfil(request):
    """Página inicial: elegir entre Estudiante o Administrador"""
    
    # Si ya está autenticado, redirigir según su rol
    if request.user.is_authenticated:
        return redireccionar_por_rol(request.user)
    
    return render(request, 'autenticacion/seleccionar_perfil.html')


# ==========================================
# LOGIN DE ESTUDIANTE
# ==========================================
def login_estudiante(request):
    """Login exclusivo para estudiantes"""
    
    if request.user.is_authenticated:
        return redirect('estudiantes:portal_estudiante')
    
    formulario = FormularioLogin()
    
    if request.method == 'POST':
        formulario = FormularioLogin(request.POST)
        
        if formulario.is_valid():
            usuario_ingresado = formulario.cleaned_data['usuario']
            contraseña = formulario.cleaned_data['contraseña']
            
            user = None
            user = authenticate(request, username=usuario_ingresado, password=contraseña)
            
            if user is None:
                try:
                    usuario_por_email = User.objects.get(email=usuario_ingresado)
                    user = authenticate(request, username=usuario_por_email.username, password=contraseña)
                except User.DoesNotExist:
                    user = None
            
            if user is not None and user.is_active:
                grupos = [g.name for g in user.groups.all()]
                
                # Verificar que sea estudiante
                if 'Estudiante' in grupos or (not user.is_staff and not user.is_superuser):
                    login(request, user)
                    messages.success(request, f'¡Bienvenido/a {user.first_name or user.username}!')
                    return redirect('estudiantes:portal_estudiante')
                else:
                    messages.error(request, '❌ Esta cuenta no es de estudiante. Usa el acceso de administrador.')
            else:
                messages.error(request, '❌ Usuario o contraseña incorrectos.')
    
    contexto = {
        'formulario': formulario,
        'tipo': 'estudiante',
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
    
    formulario = FormularioLogin()
    
    if request.method == 'POST':
        formulario = FormularioLogin(request.POST)
        
        if formulario.is_valid():
            usuario_ingresado = formulario.cleaned_data['usuario']
            contraseña = formulario.cleaned_data['contraseña']
            
            user = None
            user = authenticate(request, username=usuario_ingresado, password=contraseña)
            
            if user is None:
                try:
                    usuario_por_email = User.objects.get(email=usuario_ingresado)
                    user = authenticate(request, username=usuario_por_email.username, password=contraseña)
                except User.DoesNotExist:
                    user = None
            
            if user is not None and user.is_active:
                grupos = [g.name for g in user.groups.all()]
                
                # Verificar que sea admin o recepcionista
                if 'Administrador' in grupos or 'Recepcionista' in grupos or user.is_staff or user.is_superuser:
                    login(request, user)
                    messages.success(request, f'¡Bienvenido/a {user.first_name or user.username}!')
                    return redirect('prestamos:portal')
                else:
                    messages.error(request, '❌ Esta cuenta no es de administrador. Usa el acceso de estudiante.')
            else:
                messages.error(request, '❌ Usuario o contraseña incorrectos.')
    
    contexto = {
        'formulario': formulario,
        'tipo': 'administrador',
        'titulo_pagina': 'Login Administrador - CRAI UNEMI'
    }
    return render(request, 'autenticacion/login_admin.html', contexto)


# ==========================================
# REDIRECCIÓN POR ROL
# ==========================================
def redireccionar_por_rol(user):
    """Redirige según el rol del usuario"""
    grupos = [g.name for g in user.groups.all()]
    
    if 'Administrador' in grupos or 'Recepcionista' in grupos or user.is_staff or user.is_superuser:
        return redirect('prestamos:portal')
    else:
        return redirect('estudiantes:portal_estudiante')


# ==========================================
# LOGIN ORIGINAL (por si acaso)
# ==========================================
def pagina_login(request):
    """Login genérico - Redirige al selector"""
    return redirect('autenticacion:seleccionar_perfil')


# ==========================================
# RECUPERACIÓN, CAMBIO, ETC (se mantienen igual)
# ==========================================
def recuperar_contraseña(request):
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
                    f'Para restablecer tu contraseña, haz clic aquí: {enlace}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, '✅ Se ha enviado un enlace a tu correo.')
                return redirect('autenticacion:login_estudiante')
            except User.DoesNotExist:
                messages.error(request, '❌ No existe una cuenta con ese correo.')
    
    return render(request, 'autenticacion/recuperar_contraseña.html', {'formulario': formulario})


def cambiar_contraseña(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None
    
    if user and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            nueva = request.POST.get('nueva_contraseña')
            confirmar = request.POST.get('confirmar_contraseña')
            if nueva == confirmar and len(nueva) >= 8:
                user.set_password(nueva)
                user.save()
                messages.success(request, '✅ Contraseña cambiada. Ya puedes iniciar sesión.')
                return redirect('autenticacion:login_estudiante')
            else:
                messages.error(request, '❌ Las contraseñas no coinciden o son muy cortas.')
        return render(request, 'autenticacion/cambiar_contraseña.html')
    else:
        messages.error(request, '❌ Enlace inválido o expirado.')
        return redirect('autenticacion:login_estudiante')


def cerrar_sesion(request):
    logout(request)
    messages.success(request, '👋 Has cerrado sesión.')
    return redirect('autenticacion:seleccionar_perfil')


def soporte(request):
    return render(request, 'autenticacion/soporte.html', {'titulo_pagina': 'Soporte - CRAI UNEMI'})