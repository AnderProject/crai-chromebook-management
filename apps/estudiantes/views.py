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
                'dot': 'activo'
            })
        
        # Últimas reservas
        ultimas_reservas = Reserva.objects.filter(
            estudiante=estudiante
        ).order_by('-creado')[:3]
        
        for r in ultimas_reservas:
            if r.estado == 'pendiente':
                actividad.append({
                    'tipo': 'reserva',
                    'codigo': r.codigo_verificacion,
                    'equipo': 'Reserva pendiente',
                    'fecha': r.creado,
                    'estado': 'Pendiente',
                    'badge': 'bg-warning',
                    'dot': 'pendiente'
                })
            elif r.estado == 'completada':
                actividad.append({
                    'tipo': 'reserva',
                    'codigo': r.codigo_verificacion,
                    'equipo': 'Reserva completada',
                    'fecha': r.creado,
                    'estado': 'Completada',
                    'badge': 'bg-info',
                    'dot': 'devuelto'
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
                'dot': 'devuelto'
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
        total = Chromebook.objects.count()
        disponibles = _disponibles_efectivos()
        disponibles_manana = _disponibles_efectivos(timezone.localdate() + timedelta(days=1))
        prestados = Chromebook.objects.filter(estado='prestado').count()

        contexto = {
            'titulo_pagina': 'Reservar Chromebook - CRAI UNEMI',
            'total_chromebooks': total,
            'disponibles': disponibles,
            'disponibles_manana': disponibles_manana,
            'prestados': prestados,
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

            # Máximo un día de anticipación: solo hoy o mañana.
            if fecha > hoy + timedelta(days=1):
                return JsonResponse({
                    'success': False,
                    'message': 'Solo puedes reservar para hoy o para mañana (máximo un día de anticipación).'
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
            
            Notificacion.objects.create(
                usuario=usuario,
                titulo='Reserva Registrada',
                mensaje=f'Tu reserva ha sido registrada. Código: {codigo}. Preséntalo en el CRAI.',
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
    
    try:
        perfil = PerfilUsuario.objects.get(user=request.user)
        estudiante = Estudiante.objects.get(usuario=perfil)
        
        reservas = Reserva.objects.filter(
            estudiante=estudiante
        ).order_by('-fecha_uso', '-id')
        
        total_reservas = reservas.count()
        activas = reservas.filter(estado='pendiente').count()
        completadas = reservas.filter(estado='completada').count()
        
    except (PerfilUsuario.DoesNotExist, Estudiante.DoesNotExist):
        pass
    
    contexto = {
        'titulo_pagina': 'Mis Reservas - CRAI UNEMI',
        'reservas': reservas,
        'total_reservas': total_reservas,
        'activas': activas,
        'completadas': completadas,
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


def _reservas_estudiante_chat(estudiante, nombre=''):
    """Texto de 'Mis reservas': primero las activas (pendiente/confirmada), luego
    un historial reciente (máx. 3). Devuelve un mensaje listo para el chat."""
    from apps.prestamos.models import Reserva
    activas = list(
        Reserva.objects.filter(estudiante=estudiante,
                               estado__in=['pendiente', 'confirmada'])
        .order_by('fecha_uso', 'hora_inicio')
    )
    historial = list(
        Reserva.objects.filter(estudiante=estudiante)
        .exclude(estado__in=['pendiente', 'confirmada'])
        .order_by('-fecha_uso', '-hora_inicio')[:3]
    )
    if not activas and not historial:
        saludo = f', {nombre}' if nombre else ''
        return f'Aún no tienes reservas{saludo}. ¿Te ayudo a crear una?'
    return _formatear_reservas_chat(activas, historial, nombre)


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


def _procesar_chatbot(mensaje_raw, estudiante, perfil, session_id):
    """Lógica central del chatbot, compartida por el portal web y por WhatsApp.

    Recibe el estudiante/perfil ya identificados (por sesión en el portal, por
    teléfono en WhatsApp) y devuelve ``(respuesta, accion_realizada)``. No depende
    de ``request`` ni de la sesión, para poder reutilizarse desde cualquier canal.
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

    # --- Mis reservas ---
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

        # Damos al agente la fecha Y hora actuales para que pueda razonar (p. ej.
        # no aceptar una hora que ya pasó hoy). El horario del CRAI es 08:00–17:00.
        ahora = timezone.localtime()
        dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        contexto_tiempo = (
            f'[Ahora es {dias[ahora.weekday()]} {ahora:%Y-%m-%d} a las {ahora:%H:%M}. '
            f'Horario del CRAI: 08:00 a 17:00. No ofrezcas ni aceptes horas que ya '
            f'pasaron hoy; si piden una, dilo y sugiere una hora más tarde o mañana.] '
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

                    from apps.prestamos.views import MAX_RESERVAS_VIGENTES, _disponibles_efectivos
                    vigentes = Reserva.objects.filter(
                        estudiante=estudiante,
                        estado__in=['pendiente', 'confirmada']
                    ).count()

                    if hora_fin_dt <= hora_inicio_dt or hora_inicio_dt < dtime(8, 0) or hora_fin_dt > dtime(17, 0):
                        respuesta = (
                            'El horario de reservas es de 08:00 a 17:00 y la hora de fin '
                            'debe ser mayor que la de inicio. Intenta con otro horario.'
                        )
                    elif fecha_dt > timezone.localdate() + timedelta(days=1):
                        respuesta = (
                            'Solo puedes reservar para hoy o para mañana '
                            '(máximo un día de anticipación).'
                        )
                    elif fecha_dt < timezone.localdate() or (
                        fecha_dt == timezone.localdate()
                        and timezone.make_aware(datetime.combine(fecha_dt, hora_inicio_dt)) < timezone.localtime() - timedelta(minutes=2)
                    ):
                        ahora_local = timezone.localtime()
                        # Siguiente hora en punto a partir de ahora.
                        prox = (ahora_local + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                        if prox.date() == timezone.localdate() and prox.time() < dtime(17, 0):
                            respuesta = (
                                f'Esa hora ya pasó (ahora son las {ahora_local:%H:%M}). '
                                f'¿Te reservo desde las {prox:%H:%M}? También puedes elegir otro día.'
                            )
                        else:
                            respuesta = (
                                f'Ya terminó el horario de hoy (son las {ahora_local:%H:%M} y '
                                f'cerramos a las 17:00). ¿Reservamos para mañana?'
                            )
                    elif vigentes >= MAX_RESERVAS_VIGENTES:
                        respuesta = (
                            f'Ya tienes {MAX_RESERVAS_VIGENTES} reservas activas. Espera a que se completen '
                            'o cancela alguna antes de reservar otra.'
                        )
                    elif _disponibles_efectivos(fecha_dt) <= 0:
                        respuesta = (
                            'No quedan Chromebooks disponibles para esa fecha. '
                            'Prueba con otro día.'
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

    respuesta, accion = _procesar_chatbot(mensaje_raw, estudiante, perfil, str(request.user.id))

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

    respuesta, accion = _procesar_chatbot(mensaje_raw, estudiante, perfil, telefono or 'wa-anon')

    ChatbotConversacion.objects.create(
        usuario=perfil.user if perfil else None,
        mensaje_usuario=mensaje_raw,
        respuesta_bot=respuesta,
        canal='whatsapp',
        intencion_detectada=accion or 'conversacion',
    )
    return JsonResponse({'respuesta': respuesta, 'accion': accion})


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

    respuesta, accion = _procesar_chatbot(mensaje_raw, estudiante, perfil, telefono or 'wa-anon')

    ChatbotConversacion.objects.create(
        usuario=perfil.user if perfil else None,
        mensaje_usuario=mensaje_raw,
        respuesta_bot=respuesta,
        canal='whatsapp',
        intencion_detectada=accion or 'conversacion',
    )

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

    Notificacion.objects.create(
        usuario=perfil.user,
        titulo='Reserva Registrada',
        mensaje=f'Tu reserva ha sido registrada. Código: {codigo}. Preséntalo en el CRAI.',
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