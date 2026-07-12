def usuario_context(request):
    if not request.user.is_authenticated:
        return {}

    primer_nombre = request.user.first_name.split()[0] if request.user.first_name else 'Admin'
    primer_apellido = request.user.last_name.split()[0] if request.user.last_name else 'CRAI'
    datos = {
        'primer_nombre': primer_nombre,
        'primer_apellido': primer_apellido,
    }

    # Notificaciones de la barra superior del panel administrativo.
    # Se inyectan solo para usuarios admin (superuser / Administrador / Tics)
    # para que TODAS las plantillas del panel muestren la campana igual que el
    # dashboard, sin repetir consultas en las vistas. Las vistas que ya definen
    # estas claves (dashboard, reportes) siguen teniendo prioridad.
    es_admin = request.user.is_superuser or request.user.groups.filter(
        name__in=['Administrador', 'Tics']).exists()
    if es_admin:
        from .models import Notificacion
        recientes = list(Notificacion.objects.order_by('-fecha_envio')[:50])
        datos.update({
            'notificaciones': recientes[:5],
            'notificaciones_todas': recientes,
            'total_notificaciones': Notificacion.objects.filter(leida=False).count(),
        })

    return datos
