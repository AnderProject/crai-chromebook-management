from django.urls import path
from . import views

app_name = 'estudiantes'

urlpatterns = [
    path('portal/', views.portal_estudiante, name='portal_estudiante'),
    path('perfil/', views.perfil_estudiante, name='perfil'),
    path('perfil/foto/', views.actualizar_foto_perfil_estudiante, name='actualizar_foto_perfil'),
    path('reservar/', views.reservar_chromebook, name='reservar'),
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    path('api/cancelar-reserva/', views.api_cancelar_reserva, name='api_cancelar_reserva'),

    # Chatbot con n8n
    path('api/chatbot/', views.api_chatbot, name='api_chatbot'),
    path('api/chatbot-whatsapp/', views.api_chatbot_whatsapp, name='api_chatbot_whatsapp'),

    # Webhook directo de WhatsApp Cloud API (Meta -> Django, sin n8n)
    path('api/whatsapp/webhook/', views.webhook_whatsapp, name='webhook_whatsapp'),

    # Actividad reciente (refresco en vivo del portal)
    path('api/actividad/', views.api_actividad, name='api_actividad'),

    # APIs de consulta para n8n
    path('api/disponibilidad/', views.api_disponibilidad, name='api_disponibilidad'),
    path('api/mis-reservas/', views.api_mis_reservas, name='api_mis_reservas_n8n'),
    path('api/crear-reserva/', views.api_crear_reserva, name='api_crear_reserva_n8n'),
    path('api/info-estudiante/', views.api_info_estudiante, name='api_info_estudiante_n8n'),
    path('api/cancelar-reserva-n8n/', views.api_cancelar_reserva_n8n, name='api_cancelar_reserva_n8n'),
]