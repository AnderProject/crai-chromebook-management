from .models import SesionUsuario

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