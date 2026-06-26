from django.contrib.auth import logout

from .models import SesionUsuario


class SesionUnicaMiddleware:
    """Permite una sola sesión activa por usuario (un inicio de sesión a la vez).

    Al iniciar sesión se guarda en el perfil la session_key actual. Si llega una
    petición autenticada cuya session_key no coincide con la registrada, significa
    que el usuario volvió a iniciar sesión en otro equipo/navegador: esta sesión
    (la anterior) se cierra automáticamente.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            perfil = getattr(user, 'perfil', None)
            actual = request.session.session_key
            if perfil is not None and perfil.session_key and actual and perfil.session_key != actual:
                logout(request)
        return self.get_response(request)


class RegistrarSesionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
            navegador = request.META.get('HTTP_USER_AGENT', 'Desconocido')[:250]
            
            # Detectar sistema operativo
            if 'Windows' in navegador:
                sistema = 'Windows'
            elif 'Mac' in navegador:
                sistema = 'MacOS'
            elif 'Linux' in navegador:
                sistema = 'Linux'
            elif 'Android' in navegador:
                sistema = 'Android'
            elif 'iPhone' in navegador or 'iPad' in navegador:
                sistema = 'iOS'
            else:
                sistema = 'Desconocido'
            
            # Buscar sesión activa
            sesion = SesionUsuario.objects.filter(
                usuario=request.user, ip=ip, activa=True
            ).first()
            
            if not sesion:
                SesionUsuario.objects.create(
                    usuario=request.user,
                    ip=ip,
                    navegador=navegador,
                    sistema=sistema
                )
        
        response = self.get_response(request)
        return response