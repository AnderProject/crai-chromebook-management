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

    path('api/verificar-codigo/', views.verificar_codigo_reservacion, name='verificar_codigo_api'),
    path('api/confirmar-prestamo/', views.confirmar_prestamo, name='confirmar_prestamo_api'),

    path('api/buscar-chromebook/', views.api_buscar_chromebook, name='api_buscar_chromebook'),
    path('api/buscar-estudiante/', views.api_buscar_estudiante, name='api_buscar_estudiante'),
    path('api/registrar-prestamo/', views.api_registrar_prestamo, name='api_registrar_prestamo'),

    path('api/perfil-estudiante/<int:id>/', views.api_perfil_estudiante, name='api_perfil_estudiante'),
    path('api/devolver-prestamo/', views.api_devolver_prestamo, name='api_devolver_prestamo'),
    path('api/subir-evidencia/', views.api_subir_evidencia, name='api_subir_evidencia'),
    path('api/generar-qr-evidencia/', views.api_generar_qr_evidencia, name='api_generar_qr'),
    path('evidencia/<str:token>/', views.pagina_evidencia, name='pagina_evidencia'),
    path('api/verificar-evidencia/', views.api_verificar_evidencia, name='api_verificar_evidencia'),
    path('evidencia-foto/<str:nombre_archivo>/', views.servir_evidencia, name='servir_evidencia'),
    path('api/detalle-prestamo/<int:id>/', views.api_detalle_prestamo, name='api_detalle_prestamo'),

]