# apps/prestamos/urls.py

from django.urls import path
from . import views

app_name = 'prestamos'

urlpatterns = [
    path('portal/', views.portal, name='portal'), 
    path('dashboard/', views.dashboard, name='dashboard'),

    # Chromebooks
    path('chromebooks/', views.lista_chromebooks, name='lista_chromebooks'),
    path('chromebooks/<int:pk>/', views.detalle_chromebook, name='detalle_chromebook'),
    path('chromebooks/agregar/', views.agregar_chromebook, name='agregar_chromebook'),


    # Préstamos - Registro Rápido
    path('prestamos/', views.registro_rapido, name='lista_prestamos'),
    path('prestamos/nuevo/', views.registro_rapido, name='nuevo_prestamo'),


    path('estudiantes/', views.lista_estudiantes, name='lista_estudiantes'),

]