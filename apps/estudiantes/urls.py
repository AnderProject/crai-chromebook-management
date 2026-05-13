from django.urls import path
from . import views

app_name = 'estudiantes'

urlpatterns = [
    path('portal/', views.portal_estudiante, name='portal_estudiante'),
    path('reservar/', views.reservar_chromebook, name='reservar'),
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
]