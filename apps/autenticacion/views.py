# apps/autenticacion/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from .forms import FormularioLogin, FormularioRecuperarContraseña


# ==========================================
# VISTA DE INICIO DE SESIÓN
# ==========================================
def pagina_login(request):
    """Vista para la página de inicio de sesión"""
    
    # Si ya está autenticado, redirigir al dashboard
    if request.user.is_authenticated:
        return redirect('prestamos:dashboard')
    
    formulario = FormularioLogin()
    
    if request.method == 'POST':
        formulario = FormularioLogin(request.POST)
        
        if formulario.is_valid():
            usuario_ingresado = formulario.cleaned_data['usuario']
            contraseña = formulario.cleaned_data['contraseña']
            recordar = request.POST.get('recordarSesion', False)
            
            user = None
            
            # 1. Intentar autenticar con username
            user = authenticate(request, username=usuario_ingresado, password=contraseña)
            
            # 2. Si falla, buscar por email
            if user is None:
                try:
                    # Buscar usuario por email
                    usuario_por_email = User.objects.get(email=usuario_ingresado)
                    # Autenticar con el username encontrado
                    user = authenticate(
                        request, 
                        username=usuario_por_email.username, 
                        password=contraseña
                    )
                except User.DoesNotExist:
                    user = None
            
            # 3. Verificar autenticación
            if user is not None:
                if user.is_active:
                    login(request, user)
                    
                    # Configurar sesión según "Recordar"
                    if not recordar:
                        # La sesión expira al cerrar el navegador
                        request.session.set_expiry(0)
                    else:
                        # La sesión dura 2 semanas
                        request.session.set_expiry(1209600)
                    
                    messages.success(request, f'¡Bienvenido/a {user.first_name or user.username}!')
                    
                    # Redirigir al dashboard o a la página solicitada
                    next_url = request.GET.get('next', 'prestamos:portal')
                    return redirect(next_url)
                else:
                    messages.error(request, 'Tu cuenta está desactivada. Contacta al administrador.')
            else:
                messages.error(request, '❌ Usuario o contraseña incorrectos.')
    
    contexto = {
        'formulario': formulario,
        'titulo_pagina': 'Iniciar Sesión - CRAI UNEMI'
    }
    
    return render(request, 'autenticacion/login.html', contexto)


# ==========================================
# VISTA DE RECUPERACIÓN DE CONTRASEÑA
# ==========================================
def recuperar_contraseña(request):
    """Vista para recuperar contraseña"""
    
    formulario = FormularioRecuperarContraseña()
    
    if request.method == 'POST':
        formulario = FormularioRecuperarContraseña(request.POST)
        
        if formulario.is_valid():
            email = formulario.cleaned_data['email']
            
            try:
                # Buscar usuario por email
                user = User.objects.get(email=email)
                
                # Generar token único
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Construir enlace de restablecimiento
                enlace_recuperacion = f"http://{request.get_host()}/autenticacion/cambiar-contraseña/{uid}/{token}/"
                
                # Enviar correo
                asunto = 'Recuperación de Contraseña - CRAI UNEMI'
                mensaje = f"""
¡Hola {user.first_name or user.username}! 👋

Has solicitado restablecer tu contraseña en el sistema CRAI UNEMI.

📎 Para continuar, haz clic en el siguiente enlace:
{enlace_recuperacion}

⏰ Este enlace expirará en 24 horas.

🔒 Si no solicitaste este cambio, ignora este mensaje y tu contraseña permanecerá segura.

---
Saludos cordiales,
Equipo CRAI UNEMI
📧 crai@unemi.edu.ec
                """
                
                send_mail(
                    asunto,
                    mensaje,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                
                messages.success(request, '✅ Se ha enviado un enlace de recuperación a tu correo electrónico.')
                return redirect('autenticacion:login')
                
            except User.DoesNotExist:
                messages.error(request, '❌ No existe una cuenta con ese correo electrónico.')
            except Exception as e:
                messages.error(request, f'❌ Error al enviar el correo: {str(e)}')
    
    contexto = {
        'formulario': formulario,
        'titulo_pagina': 'Recuperar Contraseña - CRAI UNEMI'
    }
    
    return render(request, 'autenticacion/recuperar_contraseña.html', contexto)


# ==========================================
# VISTA PARA CAMBIAR CONTRASEÑA
# ==========================================
def cambiar_contraseña(request, uidb64, token):
    """Vista para cambiar la contraseña con el enlace enviado"""
    
    try:
        # Decodificar UID
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Verificar token
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            nueva_contraseña = request.POST.get('nueva_contraseña')
            confirmar_contraseña = request.POST.get('confirmar_contraseña')
            
            if nueva_contraseña == confirmar_contraseña:
                if len(nueva_contraseña) >= 8:
                    user.set_password(nueva_contraseña)
                    user.save()
                    
                    # Enviar confirmación por correo
                    asunto = 'Contraseña Cambiada - CRAI UNEMI'
                    mensaje = f"""
¡Hola {user.first_name or user.username}! 👋

Tu contraseña ha sido cambiada exitosamente en el sistema CRAI UNEMI.

Si no realizaste este cambio, contacta inmediatamente al soporte técnico:
📧 soporte.crai@unemi.edu.ec
📞 (04) 2-715-081 Ext. 1234

---
Equipo CRAI UNEMI
                    """
                    
                    try:
                        send_mail(
                            asunto,
                            mensaje,
                            settings.DEFAULT_FROM_EMAIL,
                            [user.email],
                            fail_silently=True,
                        )
                    except:
                        pass  # Si falla el correo de confirmación, no es crítico
                    
                    messages.success(request, '✅ Contraseña cambiada exitosamente. Ya puedes iniciar sesión.')
                    return redirect('autenticacion:login')
                else:
                    messages.error(request, '❌ La contraseña debe tener al menos 8 caracteres.')
            else:
                messages.error(request, '❌ Las contraseñas no coinciden.')
        
        return render(request, 'autenticacion/cambiar_contraseña.html')
    else:
        messages.error(request, '❌ El enlace de recuperación es inválido o ha expirado.')
        return redirect('autenticacion:login')


# ==========================================
# VISTA DE CERRAR SESIÓN
# ==========================================
def cerrar_sesion(request):
    """Cerrar sesión del usuario"""
    logout(request)
    messages.success(request, '👋 Has cerrado sesión correctamente.')
    return redirect('autenticacion:login')


# ==========================================
# VISTA DE SOPORTE
# ==========================================
def soporte(request):
    """Vista para la página de soporte"""
    contexto = {
        'titulo_pagina': 'Soporte Técnico - CRAI UNEMI'
    }
    return render(request, 'autenticacion/soporte.html', contexto)