# apps/autenticacion/urls.py

from django.urls import path
from . import views

app_name = 'autenticacion'

urlpatterns = [
    # Login
    path('login/', views.pagina_login, name='login'),
    
    # Logout
    path('cerrar-sesion/', views.cerrar_sesion, name='cerrar_sesion'),
    
    # Recuperar contraseña
    path('recuperar-contraseña/', views.recuperar_contraseña, name='recuperar_contraseña'),
    
    # Cambiar contraseña (con token)
    path('cambiar-contraseña/<str:uidb64>/<str:token>/', views.cambiar_contraseña, name='cambiar_contraseña'),
    
    # Soporte
    path('soporte/', views.soporte, name='soporte'),
]