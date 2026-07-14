from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.conf import settings
import random


def construir_actividad(user):
    """Construye la actividad reciente y la disponibilidad para un estudiante.

    Devuelve (actividad, disponibles, total_chromebooks). Se reutiliza tanto en
    el portal como en el endpoint de actualización en tiempo real.
    """
    from apps.prestamos.models import Chromebook, Reserva, Prestamo, Estudiante, Usuario as PerfilUsuario
    from django.utils import timezone

    # Disponibilidad real (descuenta reservas pendientes de hoy)
    from apps.prestamos.views import _disponibles_efectivos
    total_chromebooks = Chromebook.objects.count()
    disponibles = _disponibles_efectivos()

    # Actividad reciente del estudiante
    actividad = []

    try:
        perfil = PerfilUsuario.objects.get(user=user)
        estudiante = Estudiante.objects.get(usuario=perfil)

        # Préstamos activos
        prestamos_activos = Prestamo.objects.filter(
            estudiante=user,
            estado='activo'
        ).select_related('chromebook').order_by('-fecha_prestamo')[:3]
        
        for p in prestamos_activos:
            actividad.append({
                'tipo': 'prestamo',
                'codigo': p.chromebook.codigo,
                'equipo': f'{p.chromebook.marca} {p.chromebook.modelo}',
                'fecha': p.fecha_prestamo,
                'estado': 'Activo',
                'badge': 'bg-success',
                'dot': 'activo',
                'icono': 'bi-laptop',
                'detalle': (f'Devolver antes de las {timezone.localtime(p.fecha_devolucion).strftime("%H:%M")} '
                            f'del {timezone.localtime(p.fecha_devolucion).strftime("%d/%m")}')
                            if p.fecha_devolucion else 'Préstamo en curso',
            })
        
        # Últimas reservas: se muestran TODOS los estados (pendiente, completada,
        # vencida y cancelada) para que el historial del portal sea fiel.
        ETIQUETA_RESERVA = {
            'pendiente':  ('Reserva pendiente',  'Pendiente',  'bg-warning',   'pendiente'),
            'confirmada': ('Reserva confirmada', 'Confirmada', 'bg-primary',   'activo'),
            'completada': ('Reserva completada', 'Completada', 'bg-info',      'devuelto'),
            'vencida':    ('Reserva vencida',    'Vencida',    'bg-danger',    'vencido'),
            'cancelada':  ('Reserva cancelada',  'Cancelada',  'bg-secondary', 'devuelto'),
        }
        ultimas_reservas = Reserva.objects.filter(
            estudiante=estudiante
        ).select_related('chromebook').order_by('-creado')[:5]

        for r in ultimas_reservas:
            equipo, estado, badge, dot = ETIQUETA_RESERVA.get(
                r.estado, (f'Reserva {r.estado}', r.estado.title(), 'bg-secondary', 'devuelto'))
            actividad.append({
                'tipo': 'reserva',
                'codigo': r.codigo_verificacion,
                'equipo': equipo,
                'fecha': r.creado,
                'estado': estado,
                'badge': badge,
                'dot': dot,
                'icono': 'bi-calendar-check',
                'detalle': (f'Uso {r.fecha_uso.strftime("%d/%m")} · '
                            f'{r.hora_inicio.strftime("%H:%M")}–{r.hora_fin.strftime("%H:%M")}'
                            + (f' · Equipo {r.chromebook.codigo}' if r.chromebook_id else '')),
            })
        
        # Préstamos devueltos
        prestamos_devueltos = Prestamo.objects.filter(
            estudiante=user,
            estado='devuelto'
        ).select_related('chromebook').order_by('-fecha_devuelto')[:2]
        
        for p in prestamos_devueltos:
            actividad.append({
                'tipo': 'prestamo',
                'codigo': p.chromebook.codigo,
                'equipo': f'{p.chromebook.marca} {p.chromebook.modelo}',
                'fecha': p.fecha_devuelto,
                'estado': 'Devuelto',
                'badge': 'bg-secondary',
                'dot': 'devuelto',
                'icono': 'bi-check2-circle',
                'detalle': (f'Devuelto el {timezone.localtime(p.fecha_devuelto).strftime("%d/%m a las %H:%M")}'
                            if p.fecha_devuelto else 'Préstamo devuelto'),
            })
        
        # Ordenar por fecha. Se muestran ~4 a la vez (scroll interno); dejamos
        # algo más de historial para que el scroll tenga contenido.
        actividad.sort(key=lambda x: x['fecha'] if x['fecha'] else timezone.now(), reverse=True)
        actividad = actividad[:8]
        
    except (PerfilUsuario.DoesNotExist, Estudiante.DoesNotExist):
        pass

    return actividad, disponibles, total_chromebooks


@login_required
def portal_estudiante(request):
    """Portal principal del estudiante con datos reales"""
    actividad, disponibles, total_chromebooks = construir_actividad(request.user)

    numero_wa = getattr(settings, 'WHATSAPP_NUMERO', '') or ''
    whatsapp_url = (
        f'https://wa.me/{numero_wa}?text=Hola,%20soy%20estudiante%20de%20la%20UNEMI'
        if numero_wa else ''
    )

    contexto = {
        'titulo_pagina': 'Portal Estudiante - CRAI UNEMI',
        'total_chromebooks': total_chromebooks,
        'disponibles': disponibles,
        'actividad': actividad,
        'whatsapp_url': whatsapp_url,
    }
    return render(request, 'estudiantes/portal.html', contexto)


def _avisos_devolucion(user):
    """Préstamos activos del estudiante que vencen dentro de los próximos 15 min.

    Sirve para avisarle al estudiante (vía el polling del portal) que se acerca
    la hora de devolver su Chromebook. Devuelve una lista de dicts ligeros.
    """
    from apps.prestamos.models import Prestamo
    from django.utils import timezone
    from datetime import timedelta

    ahora = timezone.now()
    limite = ahora + timedelta(minutes=15)
    avisos = []
    prestamos = (Prestamo.objects
                 .filter(estudiante=user, estado='activo',
                         fecha_devolucion__gt=ahora, fecha_devolucion__lte=limite)
                 .select_related('chromebook'))
    for p in prestamos:
        restante = p.fecha_devolucion - ahora
        minutos = max(1, int(restante.total_seconds() // 60))
        avisos.append({
            'id': p.id,
            'chromebook': p.chromebook.codigo if p.chromebook_id else '',
            'minutos': minutos,
            'hora': timezone.localtime(p.fecha_devolucion).strftime('%H:%M'),
        })
    return avisos


@login_required
def api_actividad(request):
    """Devuelve la actividad reciente y la disponibilidad (para refresco en vivo del portal)."""
    actividad, disponibles, _ = construir_actividad(request.user)
    html = render_to_string('estudiantes/_actividad_lista.html', {'actividad': actividad})
    return JsonResponse({
        'html': html,
        'disponibles': disponibles,
        'avisos_devolucion': _avisos_devolucion(request.user),
    })


@login_required
def perfil_estudiante(request):
    """Perfil del estudiante: datos, edición de celular y cambio de contraseña."""
    from apps.prestamos.models import Estudiante, Usuario as PerfilUsuario

    perfil_usuario = getattr(request.user, 'perfil', None)
    estudiante = None
    if perfil_usuario is not None:
        estudiante = (
            Estudiante.objects
            .select_related('carrera')
            .filter(usuario=perfil_usuario)
            .first()
        )

    contexto = {
        'titulo_pagina': 'Mi Perfil - CRAI UNEMI',
        'perfil_usuario': perfil_usuario,
        'estudiante': estudiante,
    }
    return render(request, 'estudiantes/perfil.html', contexto)


@login_required
def actualizar_foto_perfil_estudiante(request):
    """Sube/actualiza la foto de perfil del estudiante."""
    if request.method == 'POST' and request.FILES.get('foto'):
        perfil_usuario = getattr(request.user, 'perfil', None)
        if perfil_usuario is None:
            messages.error(request, 'No se encontró el perfil del usuario.')
        else:
            perfil_usuario.foto = request.FILES['foto']
            perfil_usuario.save(update_fields=['foto'])
            messages.success(request, 'Foto de perfil actualizada.')
    return redirect('estudiantes:perfil')

def _proximo_dia_habil(d):
    """Siguiente día hábil (lunes a viernes) estrictamente después de d."""
    from datetime import timedelta
    d = d + timedelta(days=1)
    while d.weekday() >= 5:      # 5 = sábado, 6 = domingo
        d += timedelta(days=1)
    return d


def fechas_reserva_validas(hoy):
    """Las dos fechas reservables (lun-vie): hoy —o el próximo día hábil si hoy
    cae en fin de semana— y el siguiente día hábil. Así el viernes, el segundo
    botón apunta al lunes y no se permiten reservas para sábado ni domingo."""
    from datetime import timedelta
    slot1 = hoy
    while slot1.weekday() >= 5:
        slot1 += timedelta(days=1)
    return [slot1, _proximo_dia_habil(slot1)]


def _etiqueta_dia(fecha, hoy):
    """Etiqueta del botón/resumen: 'Hoy', 'Mañana' o el nombre del día."""
    from datetime import timedelta
    if fecha == hoy:
        return 'Hoy'
    if fecha == hoy + timedelta(days=1):
        return 'Mañana'
    dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    return dias[fecha.weekday()]


@login_required
def reservar_chromebook(request):
    """Vista para reservar un Chromebook"""
    from apps.prestamos.models import Reserva, Estudiante, Carrera, Chromebook
    from apps.prestamos.models import Usuario as PerfilUsuario, TipoUsuario
    from apps.prestamos.models import Notificacion
    from apps.prestamos.services.api_estudiantes import obtener_estudiante, ApiEstudiantesError
    from apps.prestamos.services.sincronizacion import sincronizar_estudiante
    from django.http import JsonResponse
    from datetime import datetime, timedelta, time as dtime
    import random
    import string

    # Horario permitido para reservas (08:00 a 17:00)
    HORA_APERTURA = dtime(8, 0)
    HORA_CIERRE = dtime(17, 0)
    from apps.prestamos.views import MAX_RESERVAS_VIGENTES
    
    # Si es GET, mostrar el formulario con datos reales
    if request.method == 'GET':
        from apps.prestamos.views import _expirar_reservas_vencidas
        _expirar_reservas_vencidas()
        # Obtener disponibilidad real (por fecha: hoy y mañana)
        from apps.prestamos.views import _disponibles_efectivos
        from django.utils import timezone
        hoy = timezone.localdate()
        slot1, slot2 = fechas_reserva_validas(hoy)
        total = Chromebook.objects.count()
        disponibles = _disponibles_efectivos(slot1)
        disponibles_manana = _disponibles_efectivos(slot2)
        prestados = Chromebook.objects.filter(estado='prestado').count()

        contexto = {
            'titulo_pagina': 'Reservar Chromebook - CRAI UNEMI',
            'total_chromebooks': total,
            'disponibles': disponibles,
            'disponibles_manana': disponibles_manana,
            'prestados': prestados,
            # Fechas reservables (lun-vie): el segundo botón salta el fin de semana.
            'fecha_slot1': slot1.strftime('%Y-%m-%d'),
            'fecha_slot2': slot2.strftime('%Y-%m-%d'),
            'label_slot1': _etiqueta_dia(slot1, hoy),
            'label_slot2': _etiqueta_dia(slot2, hoy),
        }
        return render(request, 'estudiantes/reservar.html', contexto)
    
    # Si es POST (AJAX), procesar la reserva
    if request.method == 'POST':
        try:
            motivo = request.POST.get('motivo', '')
            fecha_uso = request.POST.get('fecha_uso', '')
            hora_inicio = request.POST.get('hora_inicio', '08:00')
            hora_fin = request.POST.get('hora_fin', '')

            usuario = request.user

            # El estudiante ya debe existir como espejo local (entró por login sincronizado).
            # Sin placeholders: usamos sus datos reales provenientes de matrículas.
            try:
                perfil = PerfilUsuario.objects.get(user=usuario)
                estudiante = Estudiante.objects.get(usuario=perfil)
            except (PerfilUsuario.DoesNotExist, Estudiante.DoesNotExist):
                estudiante = None
                # Recuperación: re-sincronizar desde matrículas usando el username (cédula).
                if usuario.username.isdigit() and len(usuario.username) == 10:
                    try:
                        data = obtener_estudiante(usuario.username)
                    except ApiEstudiantesError:
                        data = None
                    if data:
                        estudiante, _ = sincronizar_estudiante(data)
                if estudiante is None:
                    return JsonResponse({
                        'success': False,
                        'message': 'Tu perfil de estudiante no está disponible. Cierra sesión e ingresa con tu cédula.'
                    })

            carrera = estudiante.carrera

            caracteres = string.ascii_uppercase + string.digits
            while True:
                codigo = ''.join(random.choices(caracteres, k=6))
                if not Reserva.objects.filter(codigo_verificacion=codigo).exists():
                    break
            
            hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M').time()
            if hora_fin:
                hora_fin_dt = datetime.strptime(hora_fin, '%H:%M').time()
            else:
                # Compatibilidad: si no llega hora_fin, usar duración (por defecto 4h)
                duracion = int(request.POST.get('duracion', 4))
                hora_fin_dt = (datetime.combine(datetime.today(), hora_inicio_dt) + timedelta(hours=duracion)).time()

            if hora_fin_dt <= hora_inicio_dt:
                return JsonResponse({
                    'success': False,
                    'message': 'La hora de fin debe ser mayor que la hora de inicio.'
                })

            if hora_inicio_dt < HORA_APERTURA or hora_fin_dt > HORA_CIERRE:
                return JsonResponse({
                    'success': False,
                    'message': 'El horario de reservas es de 08:00 a 17:00.'
                })

            # Límite de reservas vigentes (en espera o en curso) por estudiante.
            vigentes = Reserva.objects.filter(
                estudiante=estudiante,
                estado__in=['pendiente', 'confirmada']
            ).count()
            if vigentes >= MAX_RESERVAS_VIGENTES:
                return JsonResponse({
                    'success': False,
                    'message': f'Solo puedes tener {MAX_RESERVAS_VIGENTES} reservas activas a la vez. '
                               'Espera a que se completen o cancela alguna.'
                })

            from django.utils import timezone
            hoy = timezone.localdate()
            fecha = datetime.strptime(fecha_uso, '%Y-%m-%d').date() if fecha_uso else hoy
            if fecha < hoy:
                return JsonResponse({
                    'success': False,
                    'message': 'No puedes reservar en una fecha pasada.'
                })

            # Solo de lunes a viernes: no se reservan sábados ni domingos.
            if fecha.weekday() >= 5:
                return JsonResponse({
                    'success': False,
                    'message': 'No se atienden reservas los sábados ni domingos. Elige un día de lunes a viernes.'
                })

            # Solo hoy o el siguiente día hábil (el viernes, "mañana" es el lunes).
            if fecha not in fechas_reserva_validas(hoy):
                return JsonResponse({
                    'success': False,
                    'message': 'Solo puedes reservar para hoy o el siguiente día hábil.'
                })

            # Para hoy, el turno no puede haber empezado ya (evita reservas que nacen vencidas).
            # Se permite una gracia de 2 min para evitar race conditions por segundos/microsegundos.
            inicio_dt = timezone.make_aware(datetime.combine(hoy, hora_inicio_dt))
            if fecha == hoy and inicio_dt < timezone.localtime() - timedelta(minutes=2):
                return JsonResponse({
                    'success': False,
                    'message': 'Ese horario ya pasó por hoy. Elige una hora más tarde o reserva para otro día.'
                })

            # Cupo del día: no permitir más reservas que Chromebooks disponibles para esa fecha.
            from apps.prestamos.views import _disponibles_efectivos
            if _disponibles_efectivos(fecha) <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'No quedan Chromebooks disponibles para esa fecha. Elige otro día u horario.'
                })

            reserva = Reserva.objects.create(
                estudiante=estudiante,
                carrera=carrera,
                fecha_uso=fecha,
                hora_inicio=hora_inicio_dt,
                hora_fin=hora_fin_dt,
                cantidad_solicitada=1,
                estado='pendiente',
                motivo=motivo,
                codigo_verificacion=codigo
            )
            _correo_reserva_futura(reserva)

            Notificacion.objects.create(
                usuario=usuario,
                titulo='Reserva Registrada',
                mensaje=(f'Tu reserva para el {reserva.fecha_uso:%d/%m/%Y} de '
                         f'{reserva.hora_inicio:%H:%M} a {reserva.hora_fin:%H:%M} quedó registrada. '
                         'Preséntate en el CRAI para retirar tu equipo.'),
                tipo='reserva'
            )
            
            return JsonResponse({
                'success': True,
                'codigo': codigo,
                'message': 'Reserva creada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al crear la reserva: {str(e)}'
            })
@login_required
def mis_reservas(request):
    """Historial de reservas del estudiante con datos reales"""
    from apps.prestamos.models import Reserva, Estudiante, Usuario as PerfilUsuario
    from apps.prestamos.views import _expirar_reservas_vencidas

    _expirar_reservas_vencidas()

    reservas = []
    total_reservas = 0
    activas = 0
    completadas = 0
    vencidas = 0
    canceladas = 0

    try:
        perfil = PerfilUsuario.objects.get(user=request.user)
        estudiante = Estudiante.objects.get(usuario=perfil)

        # Incluye TODAS las reservas del estudiante, sin importar dónde se
        # crearon (portal, chatbot, WhatsApp o recepción/administrador).
        reservas = Reserva.objects.filter(
            estudiante=estudiante
        ).select_related('chromebook').order_by('-fecha_uso', '-id')

        total_reservas = reservas.count()
        activas = reservas.filter(estado='pendiente').count()
        completadas = reservas.filter(estado='completada').count()
        vencidas = reservas.filter(estado='vencida').count()
        canceladas = reservas.filter(estado='cancelada').count()

    except (PerfilUsuario.DoesNotExist, Estudiante.DoesNotExist):
        pass

    contexto = {
        'titulo_pagina': 'Mis Reservas - CRAI UNEMI',
        'reservas': reservas,
        'total_reservas': total_reservas,
        'activas': activas,
        'completadas': completadas,
        'vencidas': vencidas,
        'canceladas': canceladas,
    }
    return render(request, 'estudiantes/mis_reservas.html', contexto)


@login_required
def api_cancelar_reserva(request):
    """Cancela una reserva en espera del propio estudiante (desde 'Mis Reservas')."""
    from django.http import JsonResponse
    from apps.prestamos.models import Reserva, Estudiante, Usuario as PerfilUsuario
    import json

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Solicitud inválida.'}, status=400)

    reserva_id = data.get('reserva_id')
    if not reserva_id:
        return JsonResponse({'success': False, 'message': 'Falta el identificador de la reserva.'}, status=400)

    try:
        perfil = PerfilUsuario.objects.get(user=request.user)
        estudiante = Estudiante.objects.get(usuario=perfil)
    except (PerfilUsuario.DoesNotExist, Estudiante.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Tu perfil de estudiante no está disponible.'}, status=403)

    # Solo puede cancelar SUS propias reservas (el filtro por estudiante lo garantiza).
    try:
        reserva = Reserva.objects.get(id=reserva_id, estudiante=estudiante)
    except Reserva.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Reserva no encontrada.'}, status=404)

    if reserva.estado != 'pendiente':
        return JsonResponse({
            'success': False,
            'message': f'Solo puedes cancelar reservas en espera. Esta ya está {reserva.get_estado_display().lower()}.'
        })

    reserva.estado = 'cancelada'
    reserva.save()

    return JsonResponse({'success': True, 'message': 'Reserva cancelada.'})


def _correo_reserva_futura(reserva):
    """Notifica por correo al estudiante cuando su reserva es para un día POSTERIOR
    (no el mismo día). Silencioso: nunca interrumpe el flujo si falla o no hay correo.
    Se usa tanto en las reservas del portal como en las del administrador y el chatbot.
    """
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.utils import timezone
        if not reserva or not reserva.fecha_uso or reserva.fecha_uso <= timezone.localdate():
            return  # solo se avisa por correo cuando la reserva es para días posteriores
        est = getattr(reserva, 'estudiante', None)
        user = est.usuario.user if (est and getattr(est, 'usuario', None)) else None
        correo = (getattr(user, 'email', '') or '').strip()
        if not correo:
            return
        nombre = (getattr(user, 'first_name', '') or '').strip() or 'estudiante'
        fecha = reserva.fecha_uso.strftime('%d/%m/%Y')
        horario = f'{reserva.hora_inicio.strftime("%H:%M")} a {reserva.hora_fin.strftime("%H:%M")}'
        codigo = reserva.codigo_verificacion
        asunto = 'Reserva de Chromebook confirmada — CRAI UNEMI'
        texto = (
            f'Hola {nombre},\n\n'
            f'Tu reserva de Chromebook quedó registrada para el {fecha}, de {horario}.\n'
            f'Código de verificación: {codigo}\n\n'
            'Preséntate en el CRAI dentro de los primeros 15 minutos de tu horario para retirar '
            'el equipo. Si no puedes asistir, puedes cancelar la reserva desde el portal o el '
            'asistente virtual.\n\n'
            'CRAI UNEMI'
        )
        html = f'''\
<div style="font-family:Segoe UI,Arial,sans-serif;max-width:520px;margin:auto;border:1px solid #e8eaf6;border-radius:14px;overflow:hidden">
  <div style="background:linear-gradient(135deg,#1a237e,#3949ab);color:#fff;padding:20px 24px">
    <h2 style="margin:0;font-size:18px">📅 Reserva confirmada</h2>
    <p style="margin:4px 0 0;opacity:.85;font-size:13px">CRAI UNEMI</p>
  </div>
  <div style="padding:24px;color:#2b3448;font-size:14px;line-height:1.6">
    <p>Hola <b>{nombre}</b>, tu reserva de Chromebook quedó registrada para un día posterior:</p>
    <table style="width:100%;border-collapse:collapse;margin:14px 0">
      <tr><td style="padding:8px 0;color:#6b7280">📅 Fecha</td><td style="padding:8px 0;text-align:right;font-weight:600">{fecha}</td></tr>
      <tr><td style="padding:8px 0;color:#6b7280;border-top:1px solid #eef0f5">⏰ Horario</td><td style="padding:8px 0;text-align:right;font-weight:600;border-top:1px solid #eef0f5">{horario}</td></tr>
      <tr><td style="padding:8px 0;color:#6b7280;border-top:1px solid #eef0f5">🔑 Código</td><td style="padding:8px 0;text-align:right;font-weight:700;color:#1a237e;border-top:1px solid #eef0f5;letter-spacing:1px">{codigo}</td></tr>
    </table>
    <p style="background:#eef4ff;border-radius:10px;padding:12px 14px;font-size:13px;color:#1b3a8c">
      Preséntate en el CRAI dentro de los primeros 15 minutos de tu horario para retirar el equipo.
      Si no puedes asistir, cancela la reserva desde el portal o el asistente virtual.
    </p>
  </div>
</div>'''
        msg = EmailMultiAlternatives(asunto, texto, settings.DEFAULT_FROM_EMAIL, [correo])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=True)
    except Exception:
        pass


# ==========================================
# CHATBOT CON N8N
# ==========================================

def _formatear_reservas_chat(activas, historial, nombre=''):
    """Da formato legible a las reservas para el chat, separando activas e historial.

    Primero las reservas que el estudiante puede usar o cancelar (activas) y luego un
    breve historial reciente, cada una en su propio bloque (estado, código y horario).
    """
    emojis = {'pendiente': '⏳', 'confirmada': '✅', 'cancelada': '❌',
              'completada': '✔️', 'vencida': '⌛'}

    def bloque(r):
        e = emojis.get(r.estado, '📌')
        fecha = r.fecha_uso.strftime('%d/%m/%Y')
        horario = f'{r.hora_inicio.strftime("%H:%M")}–{r.hora_fin.strftime("%H:%M")}'
        return (f'{e} *{r.get_estado_display()}*\n'
                f'🔑 Código: {r.codigo_verificacion}\n'
                f'📅 {fecha}  ·  ⏰ {horario}')

    partes = [f'📋 *Tus reservas{(", " + nombre) if nombre else ""}*']
    if activas:
        partes.append('🟢 *Activas*')
        partes.extend(bloque(r) for r in activas)
    if historial:
        partes.append('🕘 *Historial reciente*')
        partes.extend(bloque(r) for r in historial)
    return '\n\n'.join(partes)


def _bloque_reserva_chat(r):
    """Formato de una reserva para el chat (estado, código y horario)."""
    emojis = {'pendiente': '⏳', 'confirmada': '✅', 'cancelada': '❌',
              'completada': '✔️', 'vencida': '⌛'}
    e = emojis.get(r.estado, '📌')
    fecha = r.fecha_uso.strftime('%d/%m/%Y')
    horario = f'{r.hora_inicio.strftime("%H:%M")}–{r.hora_fin.strftime("%H:%M")}'
    return (f'{e} *{r.get_estado_display()}*\n'
            f'🔑 Código: {r.codigo_verificacion}\n'
            f'📅 {fecha}  ·  ⏰ {horario}')


def _reservas_estudiante_chat(estudiante, nombre=''):
    """Texto de 'Mis reservas': SOLO las activas (pendiente/confirmada).
    El historial se consulta aparte pidiendo "historial"."""
    from apps.prestamos.models import Reserva
    activas = list(
        Reserva.objects.filter(estudiante=estudiante,
                               estado__in=['pendiente', 'confirmada'])
        .order_by('fecha_uso', 'hora_inicio')
    )
    if not activas:
        saludo = f', {nombre}' if nombre else ''
        return (f'No tienes reservas activas{saludo} 😌. ¿Te ayudo a crear una? '
                '(Escribe "historial" para ver tus reservas pasadas.)')
    partes = [f'📋 *Tus reservas activas{(", " + nombre) if nombre else ""}*']
    partes.extend(_bloque_reserva_chat(r) for r in activas)
    partes.append('_Escribe "historial" para ver tus reservas pasadas._')
    return '\n\n'.join(partes)


def _historial_reservas_chat(estudiante, nombre=''):
    """Texto del historial: reservas ya pasadas (canceladas/completadas/vencidas)."""
    from apps.prestamos.models import Reserva
    historial = list(
        Reserva.objects.filter(estudiante=estudiante)
        .exclude(estado__in=['pendiente', 'confirmada'])
        .order_by('-fecha_uso', '-hora_inicio')[:5]
    )
    if not historial:
        saludo = f', {nombre}' if nombre else ''
        return f'Todavía no tienes reservas en tu historial{saludo}.'
    partes = [f'🕘 *Tu historial de reservas{(", " + nombre) if nombre else ""}*']
    partes.extend(_bloque_reserva_chat(r) for r in historial)
    return '\n\n'.join(partes)


def _cancelar_reserva_por_codigo(estudiante, codigo):
    """Cancela —o explica el estado de— una reserva por su código de 6 dígitos.

    Consulta la BD real (no la deja en manos del AI). Devuelve el mensaje al usuario.
    """
    from apps.prestamos.models import Reserva
    try:
        reserva = Reserva.objects.get(codigo_verificacion=codigo, estudiante=estudiante)
    except Reserva.DoesNotExist:
        return f'No encontramos una reserva con código *{codigo}* en tu cuenta.'
    if reserva.estado in ('pendiente', 'confirmada'):
        reserva.estado = 'cancelada'
        reserva.save(update_fields=['estado'])
        return f'✅ Reserva *{codigo}* cancelada con éxito.'
    return (f'La reserva *{codigo}* ya está {reserva.get_estado_display().lower()}, '
            'así que no se puede cancelar.')


def _procesar_chatbot(mensaje_raw, estudiante, perfil, session_id, canal='web', telefono=''):
    """Lógica central del chatbot, compartida por el portal web y por WhatsApp.

    Recibe el estudiante/perfil ya identificados (por sesión en el portal, por
    teléfono en WhatsApp) y devuelve ``(respuesta, accion_realizada)``. No depende
    de ``request`` ni de la sesión, para poder reutilizarse desde cualquier canal.

    ``canal`` y ``telefono`` permiten gestionar el modo de asesoría humana
    (handoff): si el estudiante pide un asesor real, se abre una
    ``SolicitudAsesoria`` y el bot deja de responder esa conversación.
    """
    import json
    import re
    import requests
    import random
    import string
    from django.utils import timezone
    from datetime import datetime
    from apps.prestamos.models import Chromebook, Reserva

    mensaje = (mensaje_raw or '').strip().lower()

    nombre_completo = ''
    cedula = ''
    if perfil is not None:
        nombre_completo = (f'{perfil.user.first_name} {perfil.user.last_name}'.strip()
                           or perfil.user.username)
        cedula = perfil.cedula or ''
    primer_nombre = nombre_completo.split(' ')[0] if nombre_completo else ''

    # ========== ASESORÍA HUMANA (handoff) ==========
    # Se evalúa ANTES que cualquier otra lógica: si ya hay una asesoría abierta,
    # el bot guarda el mensaje para el asesor y no responde; si el estudiante pide
    # un asesor real, se abre la solicitud y el panel del CRAI recibe el aviso.
    from apps.prestamos.models import SolicitudAsesoria, MensajeAsesoria
    sid = str(session_id or 'anon')

    asesoria = SolicitudAsesoria.objects.filter(
        session_id=sid, estado__in=['pendiente', 'activa']).first()
    if asesoria:
        if mensaje in ('cancelar', 'salir', 'terminar', 'volver', 'bot', 'chatbot'):
            asesoria.estado = 'cerrada'
            asesoria.save(update_fields=['estado', 'actualizada'])
            return ('Listo, ya vuelvo a atenderte yo 🤖. ¿En qué más te ayudo?', 'asesoria_cerrada')
        # Modo humano: se guarda el mensaje para el asesor y el bot permanece en silencio.
        MensajeAsesoria.objects.create(
            solicitud=asesoria, remitente='estudiante',
            texto=(mensaje_raw or '').strip(), leido=False)
        asesoria.save(update_fields=['actualizada'])
        return ('', 'asesoria_humana')

    _KEYS_ASESOR = [
        'asesor', 'hablar con alguien', 'hablar con una persona', 'con una persona real',
        'persona real', 'ser humano', 'un humano', 'con un humano', 'atencion humana',
        'atención humana', 'agente real', 'quiero hablar con un', 'necesito hablar con un',
    ]
    if any(k in mensaje for k in _KEYS_ASESOR):
        asesoria = SolicitudAsesoria.objects.create(
            session_id=sid, canal=canal, estudiante=estudiante,
            usuario=(perfil.user if perfil else None),
            telefono=telefono or '', nombre=(nombre_completo or 'Estudiante'),
            estado='pendiente')
        MensajeAsesoria.objects.create(
            solicitud=asesoria, remitente='estudiante',
            texto=(mensaje_raw or '').strip(), leido=False)
        cuerpo = ('te comunico con un asesor del CRAI 👩‍💼. En un momento te responden por aquí. '
                  'Cuando quieras volver a hablar conmigo, escribe "cancelar".')
        respuesta = f'{primer_nombre}, {cuerpo}' if primer_nombre else cuerpo[0].upper() + cuerpo[1:]
        return (respuesta, 'solicitar_asesoria')

    # ========== PALABRAS CLAVE — respuesta directa (sin n8n) ==========
    accion_realizada = None
    respuesta = ''

    # Refrescamos el estado de las reservas antes de listar/cancelar para que una
    # reserva ya caducada no se muestre como "pendiente" ni se intente cancelar.
    from apps.prestamos.views import _expirar_reservas_vencidas
    _expirar_reservas_vencidas()

    # --- Disponibilidad ---
    if any(p in mensaje for p in ['disponibilidad', 'disponible', 'cupo', 'hay chromebook']):
        from apps.prestamos.views import _disponibles_efectivos
        disponibles = _disponibles_efectivos()
        if disponibles > 0:
            cuerpo = '¡sí hay Chromebooks disponibles! 🎉 ¿Te ayudo a reservar uno?'
        else:
            cuerpo = 'por ahora no hay Chromebooks disponibles 😕 Vuelve a consultarme en un ratito.'
        if primer_nombre:
            respuesta = f'{primer_nombre}, {cuerpo}'
        else:
            respuesta = cuerpo[0].upper() + cuerpo[1:]
        accion_realizada = 'disponibilidad'

    # --- Historial de reservas (pasadas) ---
    elif any(p in mensaje for p in ['historial', 'reservas pasada', 'reservas anterior', 'pasadas', 'anteriores']):
        if estudiante:
            respuesta = _historial_reservas_chat(estudiante, primer_nombre)
        else:
            respuesta = 'No pudimos identificar tu perfil de estudiante.'
        accion_realizada = 'historial'

    # --- Mis reservas (solo activas: pendientes/confirmadas) ---
    elif any(p in mensaje for p in ['mis reserva', 'mis reservacion', 'mis turno', 'código', 'codigo', 'mis prestamo', 'mis activo']):
        if estudiante:
            respuesta = _reservas_estudiante_chat(estudiante, primer_nombre)
        else:
            respuesta = 'No pudimos identificar tu perfil de estudiante.'
        accion_realizada = 'mis_reservas'

    # --- Cancelar por código ---
    elif 'cancelar' in mensaje or 'anular' in mensaje:
        codigo_match = re.search(r'\b(\d{6})\b', mensaje)
        if codigo_match and estudiante:
            respuesta = _cancelar_reserva_por_codigo(estudiante, codigo_match.group(1))
        elif estudiante:
            respuesta = 'Para cancelar, dime el código de 6 dígitos de la reserva. Ej: "cancelar 123456"'
        else:
            respuesta = 'No pudimos identificar tu perfil de estudiante.'
        accion_realizada = 'cancelar'

    # --- Solo el código (6 dígitos) → tratamos como cancelación ---
    # Cuando el bot pide "dame el código" y el estudiante responde solo con los 6
    # dígitos, ese mensaje no trae la palabra "cancelar"; lo resolvemos aquí contra
    # la BD en vez de mandarlo a n8n (que antes alucinaba "no encuentro la reserva").
    elif estudiante and re.fullmatch(r'\d{6}', mensaje):
        respuesta = _cancelar_reserva_por_codigo(estudiante, mensaje)
        accion_realizada = 'cancelar'

    # ========== Si no es keyword → va a n8n ==========
    if not respuesta:
        contexto_usuario = (f'[Usuario: {nombre_completo} (Cédula: {cedula})] '
                            if cedula else '[Usuario no identificado] ')

        # Damos al agente la fecha/hora actuales y las FECHAS exactas reservables
        # (hoy si es hábil + el próximo día hábil), para que no razone con un
        # "hoy o mañana" genérico —que rechazaría un lunes pedido un sábado—.
        ahora = timezone.localtime()
        dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        from apps.prestamos.views import _dias_validos_reserva
        validos = _dias_validos_reserva()
        validos_str = ' o '.join(f'{dias[d.weekday()]} {d:%Y-%m-%d}' for d in validos)
        contexto_tiempo = (
            f'[Ahora es {dias[ahora.weekday()]} {ahora:%Y-%m-%d} a las {ahora:%H:%M}. '
            f'El CRAI atiende de 08:00 a 17:00, de lunes a viernes (cerrado sábado y '
            f'domingo). Las ÚNICAS fechas reservables son: {validos_str}. No ofrezcas ni '
            f'aceptes otra fecha, ni horas que ya pasaron hoy.] '
        )
        payload = {
            'chatInput': f'{contexto_tiempo}{contexto_usuario}{(mensaje_raw or "").strip()}',
            'sessionId': str(session_id or 'anon'),
        }

        try:
            resp = requests.post(settings.N8N_CHATBOT_WEBHOOK_URL, json=payload, timeout=30)
            resp.raise_for_status()
            resp_data = resp.json()
            respuesta = resp_data.get('output', '')
        except requests.RequestException:
            respuesta = 'Uy, me colgué un segundo 😅. ¿Me lo repites?'
        except (ValueError, KeyError, IndexError, TypeError):
            respuesta = 'No te entendí bien. ¿Me lo dices de otra forma?'

        if not respuesta:
            respuesta = 'No entendí tu mensaje. ¿Puedes intentar de otra forma?'

        # ========== Parsear JSON de acción desde la respuesta del AI ==========
        json_match = re.search(r'\{\s*"action"\s*:\s*"(reservar|cancelar|mis_reservas)"', respuesta)
        if json_match:
            # Quitamos SIEMPRE el bloque JSON del texto visible al usuario: si la
            # acción luego se procesa, se sobreescribe `respuesta`; si no aplica
            # (p. ej. perfil sin registro de Estudiante), igual no se filtra el JSON.
            block_start = respuesta.index('{', json_match.start())
            block_end = respuesta.index('}', block_start) + 1
            json_str = respuesta[block_start:block_end]
            respuesta = (respuesta[:block_start] + respuesta[block_end:]).strip()
            if not respuesta:
                respuesta = '¿Necesitas algo más? Puedo ayudarte con tus reservas.'
            try:
                accion_data = json.loads(json_str)
                accion = accion_data.get('action')

                if accion == 'reservar' and estudiante:
                    fecha_uso = accion_data.get('fecha_uso', timezone.now().date().isoformat())
                    hora_inicio = accion_data.get('hora_inicio', '08:00')
                    hora_fin = accion_data.get('hora_fin', '09:00')
                    motivo = accion_data.get('motivo', '')

                    from datetime import time as dtime, timedelta
                    fecha_dt = datetime.strptime(fecha_uso, '%Y-%m-%d').date()
                    hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M').time()
                    hora_fin_dt = datetime.strptime(hora_fin, '%H:%M').time()

                    from apps.prestamos.views import (
                        MAX_RESERVAS_VIGENTES, _disponibles_en_franja,
                        _proximo_dia_habil, _dias_validos_reserva,
                    )
                    vigentes = Reserva.objects.filter(
                        estudiante=estudiante,
                        estado__in=['pendiente', 'confirmada']
                    ).count()

                    dias_validos = _dias_validos_reserva()
                    DIAS_ES = ['lunes', 'martes', 'miércoles', 'jueves',
                               'viernes', 'sábado', 'domingo']
                    def _et(d):  # etiqueta "lunes 30/06"
                        return f'{DIAS_ES[d.weekday()]} {d:%d/%m}'

                    # El estudiante elige la duración que quiera; el único límite es que
                    # toda la reserva caiga dentro del horario del CRAI (08:00–17:00).
                    if hora_fin_dt <= hora_inicio_dt or hora_inicio_dt < dtime(8, 0) or hora_fin_dt > dtime(17, 0):
                        respuesta = (
                            'El horario de reservas es de 08:00 a 17:00 y la hora de fin '
                            'debe ser mayor que la de inicio. ¿Probamos con otro horario?'
                        )
                    elif fecha_dt.weekday() >= 5:
                        prox = _proximo_dia_habil()
                        respuesta = (
                            'El CRAI atiende de lunes a viernes. '
                            f'¿Te reservo para el {_et(prox)}?'
                        )
                    elif fecha_dt not in dias_validos:
                        opciones = ' o '.join(_et(d) for d in dias_validos)
                        respuesta = (
                            f'Solo puedes reservar para hoy o el próximo día hábil ({opciones}).'
                        )
                    elif (fecha_dt == timezone.localdate()
                          and timezone.make_aware(datetime.combine(fecha_dt, hora_inicio_dt))
                              < timezone.localtime() - timedelta(minutes=2)):
                        ahora_local = timezone.localtime()
                        # Siguiente hora en punto a partir de ahora.
                        prox_hora = (ahora_local + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                        if prox_hora.time() < dtime(17, 0):
                            respuesta = (
                                f'Esa hora ya pasó (ahora son las {ahora_local:%H:%M}). '
                                f'¿Te reservo desde las {prox_hora:%H:%M}? También puedes elegir otro día.'
                            )
                        else:
                            prox_dia = _proximo_dia_habil()
                            respuesta = (
                                f'Ya terminó el horario de hoy (son las {ahora_local:%H:%M} y '
                                f'cerramos a las 17:00). ¿Reservamos para el {_et(prox_dia)}?'
                            )
                    elif vigentes >= MAX_RESERVAS_VIGENTES:
                        respuesta = (
                            f'Ya tienes {MAX_RESERVAS_VIGENTES} reservas activas. Espera a que se completen '
                            'o cancela alguna antes de reservar otra.'
                        )
                    elif _disponibles_en_franja(fecha_dt, hora_inicio_dt, hora_fin_dt) <= 0:
                        respuesta = (
                            f'Justo en ese horario ({hora_inicio}–{hora_fin}) ya no quedan '
                            'Chromebooks libres. ¿Probamos con otra hora u otro día?'
                        )
                    else:
                        while True:
                            codigo = ''.join(random.choices(string.digits, k=6))
                            if not Reserva.objects.filter(codigo_verificacion=codigo).exists():
                                break

                        reserva = Reserva.objects.create(
                            estudiante=estudiante,
                            carrera=estudiante.carrera,
                            fecha_uso=fecha_dt,
                            hora_inicio=hora_inicio_dt,
                            hora_fin=hora_fin_dt,
                            motivo=motivo or 'Reserva vía chatbot',
                            codigo_verificacion=codigo,
                            estado='pendiente',
                        )
                        _correo_reserva_futura(reserva)
                        respuesta = (
                            f'✅ *Reserva creada* · {fecha_uso}, {hora_inicio}–{hora_fin}\n'
                            f'🔑 Código: *{codigo}*\n'
                            f'Muéstralo en el CRAI para retirar tu Chromebook.'
                        )
                        accion_realizada = 'reservar'

                elif accion == 'cancelar' and estudiante:
                    codigo = accion_data.get('codigo', '')
                    if codigo:
                        respuesta = _cancelar_reserva_por_codigo(estudiante, codigo)
                    accion_realizada = 'cancelar'

                elif accion == 'mis_reservas' and estudiante:
                    respuesta = _reservas_estudiante_chat(estudiante, primer_nombre)
                    accion_realizada = 'mis_reservas'

            except (ValueError, json.JSONDecodeError):
                pass

    return respuesta, accion_realizada


@csrf_exempt
def api_chatbot(request):
    """Chatbot del portal del estudiante (identifica por la sesión iniciada)."""
    import json
    from apps.prestamos.models import ChatbotConversacion, Estudiante, Usuario as PerfilUsuario

    if request.method != 'POST':
        return JsonResponse({'success': False, 'respuesta': 'Método no permitido'}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'respuesta': 'Debes iniciar sesión'}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'respuesta': 'JSON inválido'}, status=400)

    mensaje_raw = data.get('mensaje', '')
    if not mensaje_raw.strip():
        return JsonResponse({'success': False, 'respuesta': 'Escribe un mensaje'})

    perfil = PerfilUsuario.objects.filter(user=request.user).first()
    estudiante = Estudiante.objects.filter(usuario=perfil).first() if perfil else None

    respuesta, accion = _procesar_chatbot(mensaje_raw, estudiante, perfil, str(request.user.id),
                                          canal='web')

    ChatbotConversacion.objects.create(
        usuario=request.user,
        mensaje_usuario=mensaje_raw.strip(),
        respuesta_bot=respuesta,
        canal='web',
        intencion_detectada=accion or 'conversacion',
    )
    return JsonResponse({'success': True, 'respuesta': respuesta, 'accion': accion})


@csrf_exempt
def api_chatbot_whatsapp(request):
    """Chatbot vía WhatsApp (lo invoca n8n). Identifica al estudiante por su teléfono.

    n8n envía ``{telefono, mensaje}`` y aquí se reutiliza EXACTAMENTE la misma lógica
    del portal (``_procesar_chatbot``), de modo que WhatsApp hace lo mismo que la web.
    Autenticado con ``X-N8N-KEY``.
    """
    import json
    import re
    from apps.prestamos.models import ChatbotConversacion

    api_key = request.META.get('HTTP_X_N8N_KEY', '')
    if api_key != settings.N8N_API_KEY:
        return JsonResponse({'error': 'No autorizado'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    telefono = str(data.get('telefono', '')).strip()
    mensaje_raw = str(data.get('mensaje', '')).strip()
    if not mensaje_raw:
        return JsonResponse({'respuesta': 'Escribe un mensaje.'})

    # Identificación por teléfono; si el número no está registrado, intentamos con una
    # cédula de 10 dígitos que el estudiante haya escrito en el mensaje.
    estudiante, perfil = _buscar_estudiante_n8n(telefono=telefono)
    if estudiante is None:
        m = re.search(r'\b(\d{10})\b', mensaje_raw)
        if m:
            estudiante, perfil = _buscar_estudiante_n8n(cedula=m.group(1))

    respuesta, accion = _procesar_chatbot(mensaje_raw, estudiante, perfil, telefono or 'wa-anon',
                                          canal='whatsapp', telefono=telefono)

    ChatbotConversacion.objects.create(
        usuario=perfil.user if perfil else None,
        mensaje_usuario=mensaje_raw,
        respuesta_bot=respuesta,
        canal='whatsapp',
        intencion_detectada=accion or 'conversacion',
    )
    # En modo humano el bot no responde: n8n no debe enviar nada al estudiante.
    return JsonResponse({'respuesta': respuesta, 'accion': accion, 'silencio': (accion == 'asesoria_humana')})


# ==========================================
# WEBHOOK DIRECTO DE WHATSAPP (Meta -> Django, sin n8n)
# ==========================================

# Memoria de IDs de mensajes ya procesados, para ignorar reintentos de Meta
# (Meta reenvía si no recibe 200 a tiempo). Se reinicia al reiniciar el server.
_wa_mensajes_procesados = set()


def _enviar_whatsapp(telefono, texto):
    """Envía un mensaje de texto por la Graph API de WhatsApp Cloud."""
    import requests
    token = settings.WHATSAPP_ACCESS_TOKEN
    pnid = settings.WHATSAPP_PHONE_NUMBER_ID
    if not token or not pnid:
        return False, 'Falta WHATSAPP_ACCESS_TOKEN o WHATSAPP_PHONE_NUMBER_ID en .env'
    url = f'https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{pnid}/messages'
    payload = {
        'messaging_product': 'whatsapp',
        'to': telefono,
        'type': 'text',
        'text': {'body': texto[:4096]},
    }
    try:
        r = requests.post(
            url, json=payload,
            headers={'Authorization': f'Bearer {token}'},
            timeout=15,
        )
        if r.status_code >= 400:
            return False, r.text[:300]
        return True, ''
    except requests.RequestException as e:
        return False, str(e)


# Botones del menú principal de WhatsApp (id -> título). El título no debe pasar
# de 20 caracteres (límite de la Cloud API).
_WA_MENU_BOTONES = [
    ('menu_reservar', '📅 Reservar'),
    ('menu_mis', '📋 Mis reservas'),
    ('menu_cancelar', '❌ Cancelar'),
]

# Lo que "escribe" cada botón al pulsarse (se procesa igual que un mensaje normal).
_WA_MENU_INTENCIONES = {
    'menu_reservar': 'quiero reservar un chromebook',
    'menu_mis': 'mis reservas',
    'menu_cancelar': 'cancelar',
}


def _enviar_whatsapp_menu(telefono, texto):
    """Envía un mensaje interactivo con los 3 botones del menú principal.

    El cuerpo (``texto``) es el mensaje que acompaña a los botones; sirve tanto para
    el saludo ('¿En qué te ayudo?') como para un cierre tras una acción ('¿Algo más?').
    """
    import requests
    token = settings.WHATSAPP_ACCESS_TOKEN
    pnid = settings.WHATSAPP_PHONE_NUMBER_ID
    if not token or not pnid:
        return False, 'Falta WHATSAPP_ACCESS_TOKEN o WHATSAPP_PHONE_NUMBER_ID en .env'
    url = f'https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{pnid}/messages'
    payload = {
        'messaging_product': 'whatsapp',
        'to': telefono,
        'type': 'interactive',
        'interactive': {
            'type': 'button',
            'body': {'text': (texto or '¿En qué te ayudo?')[:1024]},
            'action': {'buttons': [
                {'type': 'reply', 'reply': {'id': bid, 'title': titulo}}
                for bid, titulo in _WA_MENU_BOTONES
            ]},
        },
    }
    try:
        r = requests.post(
            url, json=payload,
            headers={'Authorization': f'Bearer {token}'},
            timeout=15,
        )
        if r.status_code >= 400:
            return False, r.text[:300]
        return True, ''
    except requests.RequestException as e:
        return False, str(e)


@csrf_exempt
def webhook_whatsapp(request):
    """Webhook directo de WhatsApp Cloud API.

    GET  -> verificación del webhook de Meta (responde el hub.challenge).
    POST -> mensaje entrante: identifica al estudiante por teléfono, reutiliza
            ``_procesar_chatbot`` y responde por la Graph API.
    """
    import json
    import re
    from django.http import HttpResponse
    from apps.prestamos.models import ChatbotConversacion

    # --- Verificación del webhook (Meta hace un GET una sola vez) ---
    if request.method == 'GET':
        modo = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge', '')
        if modo == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge, content_type='text/plain')
        return HttpResponse('Token de verificación inválido', status=403)

    if request.method != 'POST':
        return HttpResponse(status=405)

    # --- Mensaje entrante ---
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return HttpResponse(status=200)  # 200 para que Meta no reintente

    # Extraer el primer mensaje del payload de Meta (texto o botón pulsado).
    telefono = mensaje_raw = msg_id = ''
    try:
        value = data['entry'][0]['changes'][0]['value']
        mensajes = value.get('messages') or []
        if mensajes:
            m = mensajes[0]
            msg_id = m.get('id', '')
            telefono = m.get('from', '')
            tipo = m.get('type')
            if tipo == 'text':
                mensaje_raw = (m.get('text') or {}).get('body', '')
            elif tipo == 'interactive':
                # El usuario pulsó un botón: lo traducimos a su intención de texto.
                inter = m.get('interactive') or {}
                resp_btn = inter.get('button_reply') or inter.get('list_reply') or {}
                boton_id = resp_btn.get('id', '')
                mensaje_raw = _WA_MENU_INTENCIONES.get(boton_id, resp_btn.get('title', ''))
    except (KeyError, IndexError, TypeError):
        pass

    # Sin texto (status de entrega, audio, etc.) o reintento ya visto -> 200 y salir.
    if not telefono or not mensaje_raw:
        return HttpResponse(status=200)
    if msg_id and msg_id in _wa_mensajes_procesados:
        return HttpResponse(status=200)
    if msg_id:
        _wa_mensajes_procesados.add(msg_id)

    # Identificación SOLO por el número de WhatsApp: debe coincidir con el teléfono
    # registrado en un perfil. Si el número no está registrado, no lo atendemos
    # (el bot solo responde a estudiantes registrados en la base).
    estudiante, perfil = _buscar_estudiante_n8n(telefono=telefono)
    if perfil is None:
        aviso = ('Hola. Este número no está registrado en el CRAI UNEMI, así que no '
                 'puedo atenderte por aquí. Si eres estudiante, acércate al CRAI para '
                 'vincular tu número y luego escríbeme.')
        _enviar_whatsapp(telefono, aviso)
        ChatbotConversacion.objects.create(
            usuario=None,
            mensaje_usuario=mensaje_raw,
            respuesta_bot=aviso,
            canal='whatsapp',
            intencion_detectada='no_registrado',
        )
        return HttpResponse(status=200)

    primer_nombre = ''
    if perfil is not None:
        nombre = (f'{perfil.user.first_name} {perfil.user.last_name}'.strip()
                  or perfil.user.username)
        primer_nombre = nombre.split(' ')[0]

    # --- Saludo / menú: mostramos el menú de botones (atajo, sin pasar por n8n) ---
    norm = re.sub(r'[^0-9a-záéíóúñü ]', '', mensaje_raw.strip().lower()).strip()
    MENU_TRIGGERS = {
        'hola', 'holi', 'holaa', 'buenas', 'buenos dias', 'buenas tardes',
        'buenas noches', 'hey', 'ola', 'menu', 'menú', 'opciones', 'ayuda',
        'inicio', 'empezar', 'start',
    }
    if norm in MENU_TRIGGERS:
        saludo = f'¡Hola {primer_nombre}! ' if primer_nombre else '¡Hola! '
        cuerpo = f'{saludo}¿En qué te ayudo?'
        _enviar_whatsapp_menu(telefono, cuerpo)
        ChatbotConversacion.objects.create(
            usuario=perfil.user if perfil else None,
            mensaje_usuario=mensaje_raw,
            respuesta_bot=cuerpo,
            canal='whatsapp',
            intencion_detectada='menu',
        )
        return HttpResponse(status=200)

    respuesta, accion = _procesar_chatbot(mensaje_raw, estudiante, perfil, telefono or 'wa-anon',
                                          canal='whatsapp', telefono=telefono)

    ChatbotConversacion.objects.create(
        usuario=perfil.user if perfil else None,
        mensaje_usuario=mensaje_raw,
        respuesta_bot=respuesta,
        canal='whatsapp',
        intencion_detectada=accion or 'conversacion',
    )

    # En modo asesoría humana el bot permanece en silencio (el asesor responde
    # por su cuenta desde el panel del CRAI): no se envía nada al estudiante.
    if accion == 'asesoria_humana' or not (respuesta or '').strip():
        return HttpResponse(status=200)

    # Tras completar una acción (reserva creada o cancelada, que empiezan con ✅),
    # acompañamos la confirmación con el menú de botones a modo de "¿algo más?".
    if respuesta.startswith('✅'):
        _enviar_whatsapp_menu(telefono, respuesta)
    else:
        _enviar_whatsapp(telefono, respuesta)
    return HttpResponse(status=200)


# ==========================================
# APIs DE CONSULTA PARA N8N
# ==========================================

def _buscar_estudiante_n8n(cedula='', telefono=''):
    """Localiza un Estudiante por cédula o por teléfono (para n8n / WhatsApp).

    El número que envía WhatsApp llega en formato internacional (ej. 5939XXXXXXXX),
    mientras que en la BD el teléfono se guarda como 10 dígitos (09XXXXXXXX). Para
    casarlos comparamos los últimos 9 dígitos (el número nacional sin el 0 ni el 593).
    Devuelve (estudiante, perfil) o (None, None).
    """
    import re
    from apps.prestamos.models import Estudiante, Usuario as PerfilUsuario

    cedula = (cedula or '').strip()
    telefono = (telefono or '').strip()

    perfil = None
    if cedula:
        perfil = PerfilUsuario.objects.filter(cedula=cedula).first()

    if perfil is None and telefono:
        digitos = re.sub(r'\D', '', telefono)
        ultimos9 = digitos[-9:] if len(digitos) >= 9 else ''
        if ultimos9:
            perfil = (
                PerfilUsuario.objects
                .filter(telefono__endswith=ultimos9)
                .exclude(telefono__isnull=True)
                .exclude(telefono='')
                .first()
            )

    if perfil is None:
        return None, None

    estudiante = Estudiante.objects.filter(usuario=perfil).first()
    return estudiante, perfil


def api_info_estudiante(request):
    """Devuelve datos del estudiante por cédula o por teléfono (para n8n)."""
    api_key = request.META.get('HTTP_X_N8N_KEY', '')
    if api_key != settings.N8N_API_KEY:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    cedula = request.GET.get('cedula', '').strip()
    telefono = request.GET.get('telefono', '').strip()
    if not cedula and not telefono:
        return JsonResponse({'error': 'Indica cedula o telefono'}, status=400)

    estudiante, perfil = _buscar_estudiante_n8n(cedula=cedula, telefono=telefono)
    if estudiante is None:
        return JsonResponse({'error': 'Estudiante no encontrado'}, status=404)

    return JsonResponse({
        'encontrado': True,
        'cedula': perfil.cedula,
        'nombres': perfil.user.first_name,
        'apellidos': perfil.user.last_name,
        'nombre_completo': (f'{perfil.user.first_name} {perfil.user.last_name}'.strip()
                            or perfil.user.username),
        'carrera': estudiante.carrera.nombre if estudiante.carrera else 'No registrada',
        'semestre': estudiante.semestre,
    })


@csrf_exempt
def api_crear_reserva(request):
    """Crea una reserva desde n8n (autenticado con X-N8N-KEY). Acepta duracion o hora_fin."""
    import json
    from datetime import datetime, timedelta, time as dtime
    import random
    import string
    from apps.prestamos.models import Reserva, Estudiante, Carrera, Notificacion
    from apps.prestamos.models import Usuario as PerfilUsuario

    api_key = request.META.get('HTTP_X_N8N_KEY', '')
    if api_key != settings.N8N_API_KEY:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    cedula = data.get('cedula', '').strip()
    telefono = data.get('telefono', '').strip()
    fecha_uso = data.get('fecha_uso', '').strip()
    hora_inicio = data.get('hora_inicio', '08:00').strip()
    hora_fin = data.get('hora_fin', '').strip()
    motivo = data.get('motivo', '').strip()

    if not cedula and not telefono:
        return JsonResponse({'error': 'Indica cedula o telefono'}, status=400)
    if not fecha_uso:
        return JsonResponse({'error': 'Parámetro fecha_uso requerido'}, status=400)

    estudiante, perfil = _buscar_estudiante_n8n(cedula=cedula, telefono=telefono)
    if estudiante is None:
        return JsonResponse({'error': 'Estudiante no encontrado'}, status=404)

    carrera = estudiante.carrera

    caracteres = string.ascii_uppercase + string.digits
    while True:
        codigo = ''.join(random.choices(caracteres, k=6))
        if not Reserva.objects.filter(codigo_verificacion=codigo).exists():
            break

    hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M').time()

    if hora_fin:
        hora_fin_dt = datetime.strptime(hora_fin, '%H:%M').time()
    else:
        duracion = int(data.get('duracion', 4))
        hora_fin_dt = (datetime.combine(datetime.today(), hora_inicio_dt) + timedelta(hours=duracion)).time()

    if hora_fin_dt <= hora_inicio_dt:
        return JsonResponse({'error': 'La hora de fin debe ser mayor que la de inicio'}, status=400)
    if hora_inicio_dt < dtime(8, 0) or hora_fin_dt > dtime(17, 0):
        return JsonResponse({'error': 'El horario de reservas es de 08:00 a 17:00'}, status=400)

    from apps.prestamos.views import MAX_RESERVAS_VIGENTES
    vigentes = Reserva.objects.filter(
        estudiante=estudiante,
        estado__in=['pendiente', 'confirmada']
    ).count()
    if vigentes >= MAX_RESERVAS_VIGENTES:
        return JsonResponse({'error': f'El estudiante ya tiene {MAX_RESERVAS_VIGENTES} reservas activas'}, status=400)

    fecha = datetime.strptime(fecha_uso, '%Y-%m-%d').date()

    from apps.prestamos.views import _disponibles_efectivos
    if _disponibles_efectivos(fecha) <= 0:
        return JsonResponse({'error': 'No quedan Chromebooks disponibles para esa fecha'}, status=400)

    reserva = Reserva.objects.create(
        estudiante=estudiante,
        carrera=carrera,
        fecha_uso=fecha,
        hora_inicio=hora_inicio_dt,
        hora_fin=hora_fin_dt,
        cantidad_solicitada=1,
        estado='pendiente',
        motivo=motivo,
        codigo_verificacion=codigo,
    )
    _correo_reserva_futura(reserva)

    Notificacion.objects.create(
        usuario=perfil.user,
        titulo='Reserva Registrada',
        mensaje=(f'Tu reserva para el {reserva.fecha_uso:%d/%m/%Y} de '
                 f'{reserva.hora_inicio:%H:%M} a {reserva.hora_fin:%H:%M} quedó registrada. '
                 'Preséntate en el CRAI para retirar tu equipo.'),
        tipo='reserva',
    )

    return JsonResponse({
        'success': True,
        'reserva_id': reserva.id,
        'codigo': codigo,
        'fecha': fecha_uso,
        'inicio': hora_inicio,
        'fin': hora_fin_dt.strftime('%H:%M'),
        'estado': 'pendiente',
    })

@csrf_exempt
def api_cancelar_reserva_n8n(request):
    """Cancela una reserva desde n8n (autenticado con X-N8N-KEY) por cédula + código."""
    import json
    from apps.prestamos.models import Reserva

    api_key = request.META.get('HTTP_X_N8N_KEY', '')
    if api_key != settings.N8N_API_KEY:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    cedula = data.get('cedula', '').strip()
    codigo = data.get('codigo', '').strip()
    telefono = data.get('telefono', '').strip()
    if not codigo:
        return JsonResponse({'error': 'Parámetro codigo requerido'}, status=400)

    estudiante, _perfil = _buscar_estudiante_n8n(cedula=cedula, telefono=telefono)
    if estudiante is None:
        return JsonResponse({'error': 'Estudiante no encontrado'}, status=404)

    try:
        reserva = Reserva.objects.get(codigo_verificacion=codigo, estudiante=estudiante)
    except Reserva.DoesNotExist:
        return JsonResponse({'error': 'No encontramos una reserva con ese código en tu cuenta'}, status=404)

    if reserva.estado not in ('pendiente', 'confirmada'):
        return JsonResponse({
            'error': f'La reserva {codigo} ya está {reserva.get_estado_display().lower()} y no se puede cancelar',
        }, status=400)

    reserva.estado = 'cancelada'
    reserva.save(update_fields=['estado'])
    return JsonResponse({'success': True, 'codigo': codigo, 'estado': 'cancelada'})


def api_disponibilidad(request):
    """Devuelve disponibilidad actual de Chromebooks (para n8n)."""
    from apps.prestamos.models import Chromebook

    api_key = request.META.get('HTTP_X_N8N_KEY', '')
    if api_key != settings.N8N_API_KEY:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    from apps.prestamos.views import _disponibles_efectivos
    total = Chromebook.objects.count()
    disponibles = _disponibles_efectivos()
    prestados = Chromebook.objects.filter(estado='prestado').count()

    return JsonResponse({
        'total': total,
        'disponibles': disponibles,
        'prestados': prestados,
    })


def api_mis_reservas(request):
    """Devuelve reservas y préstamos activos de un estudiante (para n8n)."""
    from apps.prestamos.models import Reserva, Prestamo, Estudiante, Usuario as PerfilUsuario

    api_key = request.META.get('HTTP_X_N8N_KEY', '')
    if api_key != settings.N8N_API_KEY:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    cedula = request.GET.get('cedula', '').strip()
    telefono = request.GET.get('telefono', '').strip()
    if not cedula and not telefono:
        return JsonResponse({'error': 'Indica cedula o telefono'}, status=400)

    estudiante, perfil = _buscar_estudiante_n8n(cedula=cedula, telefono=telefono)
    if estudiante is None:
        return JsonResponse({'reservas': [], 'prestamos': []})

    # Últimas reservas
    reservas = Reserva.objects.filter(estudiante=estudiante).order_by('-fecha_uso')[:5]
    reservas_data = [{
        'estado': r.estado,
        'codigo': r.codigo_verificacion,
        'fecha': r.fecha_uso.isoformat(),
        'inicio': r.hora_inicio.strftime('%H:%M'),
        'fin': r.hora_fin.strftime('%H:%M'),
    } for r in reservas]

    # Préstamos activos del usuario
    prestamos = Prestamo.objects.filter(estudiante=perfil.user, estado='activo').select_related('chromebook')
    prestamos_data = [{
        'chromebook': p.chromebook.codigo,
        'inicio': p.fecha_prestamo.isoformat(),
        'devolucion': p.fecha_devolucion.isoformat(),
    } for p in prestamos]

    return JsonResponse({'reservas': reservas_data, 'prestamos': prestamos_data})

@login_required
def api_asesoria_mis_mensajes(request):
    """Polling del estudiante web: mensajes nuevos del asesor de su asesoría activa."""
    from apps.prestamos.models import SolicitudAsesoria
    from django.utils import timezone
    try:
        desde = int(request.GET.get('desde', 0) or 0)
    except (ValueError, TypeError):
        desde = 0
    s = SolicitudAsesoria.objects.filter(
        session_id=str(request.user.id), estado__in=['pendiente', 'activa']).first()
    if not s:
        return JsonResponse({'activa': False, 'mensajes': [], 'ultimo_id': desde})
    qs = s.mensajes.filter(remitente='asesor', id__gt=desde).order_by('id')
    msgs = [{'id': m.id, 'texto': m.texto,
             'hora': timezone.localtime(m.creado).strftime('%H:%M')} for m in qs]
    ultimo_id = msgs[-1]['id'] if msgs else desde
    return JsonResponse({'activa': True, 'mensajes': msgs, 'ultimo_id': ultimo_id})
