from django.urls import path
from . import views

app_name = 'autenticacion'

urlpatterns = [
    # Selector de perfil (página inicial)
    path('', views.seleccionar_perfil, name='seleccionar_perfil'),
    
    # Login por rol
    path('login/estudiante/', views.login_estudiante, name='login_estudiante'),
    path('login/administrador/', views.login_administrador, name='login_administrador'),
    
    # Login genérico (redirige al selector)
    path('login/', views.pagina_login, name='login'),
    
    # Otras
    path('cerrar-sesion/', views.cerrar_sesion, name='cerrar_sesion'),
    path('recuperar-contraseña/', views.recuperar_contraseña, name='recuperar_contraseña'),
    path('cambiar-contraseña/<str:uidb64>/<str:token>/', views.cambiar_contraseña, name='cambiar_contraseña'),
    path('soporte/', views.soporte, name='soporte'),
]