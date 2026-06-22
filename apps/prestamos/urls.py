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
    path('api/revelar-codigo-reserva/', views.revelar_codigo_reserva, name='revelar_codigo_reserva'),
    path('api/confirmar-prestamo/', views.confirmar_prestamo, name='confirmar_prestamo_api'),

    path('api/buscar-chromebook/', views.api_buscar_chromebook, name='api_buscar_chromebook'),
    path('api/buscar-estudiante/', views.api_buscar_estudiante, name='api_buscar_estudiante'),
    path('api/registrar-prestamo/', views.api_registrar_prestamo, name='api_registrar_prestamo'),

    path('api/perfil-estudiante/<int:id>/', views.api_perfil_estudiante, name='api_perfil_estudiante'),
    path('api/devolver-prestamo/', views.api_devolver_prestamo, name='api_devolver_prestamo'),
    path('api/subir-evidencia/', views.api_subir_evidencia, name='api_subir_evidencia'),
    path('api/subir-evidencia-webcam/', views.api_subir_evidencia_webcam, name='api_subir_evidencia_webcam'),
    path('api/generar-qr-evidencia/', views.api_generar_qr_evidencia, name='api_generar_qr'),
    path('evidencia/<str:token>/', views.pagina_evidencia, name='pagina_evidencia'),
    path('api/verificar-evidencia/', views.api_verificar_evidencia, name='api_verificar_evidencia'),
    path('evidencia-foto/<str:nombre_archivo>/', views.servir_evidencia, name='servir_evidencia'),
    path('api/detalle-prestamo/<int:id>/', views.api_detalle_prestamo, name='api_detalle_prestamo'),
    path('ficha-estudiantil/', views.ficha_estudiantil, name='ficha_estudiantil'),
    path('mantenimiento/', views.lista_mantenimientos, name='lista_mantenimientos'),
    path('mantenimiento/agregar/', views.agregar_mantenimiento, name='agregar_mantenimiento'),
    path('mantenimiento/finalizar/<int:id>/', views.finalizar_mantenimiento, name='finalizar_mantenimiento'),
    path('api/detalle-mantenimiento/<int:id>/', views.api_detalle_mantenimiento, name='api_detalle_mantenimiento'),
    path('api/editar-mantenimiento/<int:id>/', views.api_editar_mantenimiento, name='api_editar_mantenimiento'),
    path('ajustes/', views.ajustes, name='ajustes'),
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/foto/', views.actualizar_foto_perfil, name='actualizar_foto_perfil'),
    path('api/perfil/telefono/', views.api_actualizar_telefono, name='api_actualizar_telefono'),
    path('api/perfil/password/solicitar/', views.api_solicitar_codigo_password, name='api_solicitar_codigo_password'),
    path('api/perfil/password/confirmar/', views.api_confirmar_codigo_password, name='api_confirmar_codigo_password'),
    path('reportes/', views.reportes, name='reportes'),

    # TICs: gestión de personal (crear recepcionistas)
    path('personal/', views.gestion_personal, name='gestion_personal'),
    path('api/detalle-chromebook/<int:id>/', views.api_detalle_chromebook, name='api_detalle_chromebook'),
    path('api/editar-chromebook/<int:id>/', views.api_editar_chromebook, name='api_editar_chromebook'),
    path('api/generar-qr-foto-chromebook/', views.api_generar_qr_foto_chromebook, name='api_generar_qr_foto'),
    path('subir-foto-chromebook/<str:token>/', views.subir_foto_chromebook, name='subir_foto_chromebook'),

    # API de integración con matrículas
    path('api/test-conexion/', views.api_test_conexion, name='api_test_conexion'),
    path('api/sincronizar/', views.api_sincronizar_estudiantes, name='api_sincronizar'),
    path('api/toggle-matriculas/', views.api_toggle_matriculas, name='api_toggle_matriculas'),

    # APIs de actualización en vivo (admin)
    path('api/dashboard-stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/prestamos-hoy/', views.api_prestamos_hoy, name='api_prestamos_hoy'),
    path('api/chromebooks-estado/', views.api_chromebooks_estado, name='api_chromebooks_estado'),
    path('api/monitoreo/', views.api_monitoreo, name='api_monitoreo'),
    path('api/reportes-temporal/', views.api_reportes_temporal, name='api_reportes_temporal'),

]