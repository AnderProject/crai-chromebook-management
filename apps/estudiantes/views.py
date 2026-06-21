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

    # Disponibilidad real
    total_chromebooks = Chromebook.objects.count()
    disponibles = Chromebook.objects.filter(estado='disponible').count()

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
        
        # Ordenar por fecha y limitar a 5
        actividad.sort(key=lambda x: x['fecha'] if x['fecha'] else timezone.now(), reverse=True)
        actividad = actividad[:5]
        
    except (PerfilUsuario.DoesNotExist, Estudiante.DoesNotExist):
        pass

    return actividad, disponibles, total_chromebooks


@login_required
def portal_estudiante(request):
    """Portal principal del estudiante con datos reales"""
    actividad, disponibles, total_chromebooks = construir_actividad(request.user)

    contexto = {
        'titulo_pagina': 'Portal Estudiante - CRAI UNEMI',
        'total_chromebooks': total_chromebooks,
        'disponibles': disponibles,
        'actividad': actividad,
    }
    return render(request, 'estudiantes/portal.html', contexto)


@login_required
def api_actividad(request):
    """Devuelve la actividad reciente y la disponibilidad (para refresco en vivo del portal)."""
    actividad, disponibles, _ = construir_actividad(request.user)
    html = render_to_string('estudiantes/_actividad_lista.html', {'actividad': actividad})
    return JsonResponse({'html': html, 'disponibles': disponibles})

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
    MAX_RESERVAS_VIGENTES = 2
    
    # Si es GET, mostrar el formulario con datos reales
    if request.method == 'GET':
        from apps.prestamos.views import _expirar_reservas_vencidas
        _expirar_reservas_vencidas()
        # Obtener disponibilidad real
        total = Chromebook.objects.count()
        disponibles = Chromebook.objects.filter(estado='disponible').count()
        prestados = Chromebook.objects.filter(estado='prestado').count()
        
        contexto = {
            'titulo_pagina': 'Reservar Chromebook - CRAI UNEMI',
            'total_chromebooks': total,
            'disponibles': disponibles,
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
            if fecha == hoy and hora_inicio_dt <= timezone.localtime().time():
                return JsonResponse({
                    'success': False,
                    'message': 'Ese horario ya pasó por hoy. Elige una hora más tarde o reserva para otro día.'
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

@csrf_exempt
def api_chatbot(request):
    """
    Chatbot híbrido:
    - Keywords comunes se responden directo desde Django.
    - Crear reserva requiere conversación → va a n8n.
    - El AI de n8n puede devolver JSON con acciones.
    """
    import json
    import re
    import requests
    import random
    import string
    from django.utils import timezone
    from datetime import datetime
    from apps.prestamos.models import ChatbotConversacion, Chromebook, Reserva, Estudiante, Usuario as PerfilUsuario

    if request.method != 'POST':
        return JsonResponse({'success': False, 'respuesta': 'Método no permitido'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'respuesta': 'Debes iniciar sesión'}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'respuesta': 'JSON inválido'}, status=400)

    mensaje = data.get('mensaje', '').strip().lower()
    if not mensaje:
        return JsonResponse({'success': False, 'respuesta': 'Escribe un mensaje'})

    # ========== Identificar estudiante autenticado ==========
    perfil = None
    estudiante = None
    nombre_completo = ''
    cedula = ''
    try:
        perfil = PerfilUsuario.objects.get(user=request.user)
        estudiante = Estudiante.objects.get(usuario=perfil)
        nombre_completo = (f'{perfil.user.first_name} {perfil.user.last_name}'.strip()
                           or perfil.user.username)
        cedula = perfil.cedula
    except (PerfilUsuario.DoesNotExist, Estudiante.DoesNotExist):
        pass

    # ========== PALABRAS CLAVE — respuesta directa (sin n8n) ==========
    accion_realizada = None
    respuesta = ''

    # --- Disponibilidad ---
    if any(p in mensaje for p in ['disponibilidad', 'disponible', 'cupo', 'hay chromebook']):
        total = Chromebook.objects.count()
        disponibles = Chromebook.objects.filter(estado='disponible').count()
        en_prestamo = Chromebook.objects.filter(estado='prestado').count()
        en_mantenimiento = Chromebook.objects.filter(estado='mantenimiento').count()

        respuesta = (
            f'📊 *Disponibilidad de Chromebooks*\n\n'
            f'✅ Disponibles: {disponibles}\n'
            f'📤 En préstamo: {en_prestamo}\n'
            f'🔧 En mantenimiento: {en_mantenimiento}\n'
            f'📦 Total: {total}\n\n'
            f'{"Hay equipos disponibles para reservar 🎉" if disponibles > 0 else "No hay equipos disponibles en este momento 😕"}'
        )
        if nombre_completo:
            respuesta = f'Hola {nombre_completo},\n\n' + respuesta
        accion_realizada = 'disponibilidad'

    # --- Mis reservas ---
    elif any(p in mensaje for p in ['mis reserva', 'mis reservacion', 'mis turno', 'código', 'codigo', 'mis prestamo', 'mis activo']):
        if estudiante:
            reservas = Reserva.objects.filter(estudiante=estudiante).order_by('-fecha_uso')[:5]
            if reservas:
                lines = [f'📋 *Tus últimas reservas ({nombre_completo})*']
                for r in reservas:
                    estado_emoji = {'pendiente': '⏳', 'confirmada': '✅', 'cancelada': '❌', 'completada': '✔️'}
                    emoji = estado_emoji.get(r.estado, '❓')
                    lines.append(
                        f'\n{emoji} *{r.codigo_verificacion}* — {r.fecha_uso} '
                        f'{r.hora_inicio.strftime("%H:%M")}-{r.hora_fin.strftime("%H:%M")} '
                        f'({r.get_estado_display()})'
                    )
                respuesta = '\n'.join(lines)
            else:
                respuesta = f'No tienes reservas registradas, {nombre_completo}. ¿Quieres hacer una?'
        else:
            respuesta = 'No pudimos identificar tu perfil de estudiante.'
        accion_realizada = 'mis_reservas'

    # --- Cancelar por código ---
    elif 'cancelar' in mensaje or 'anular' in mensaje:
        codigo_match = re.search(r'\b(\d{6})\b', mensaje)
        if codigo_match and estudiante:
            codigo = codigo_match.group(1)
            try:
                reserva = Reserva.objects.get(codigo_verificacion=codigo, estudiante=estudiante)
                if reserva.estado in ('pendiente', 'confirmada'):
                    reserva.estado = 'cancelada'
                    reserva.save(update_fields=['estado'])
                    respuesta = f'✅ Reserva *{codigo}* cancelada con éxito.'
                else:
                    respuesta = f'La reserva *{codigo}* ya está {reserva.get_estado_display()}. No se puede cancelar.'
            except Reserva.DoesNotExist:
                respuesta = f'No encontramos una reserva con código *{codigo}* en tu cuenta.'
        elif estudiante:
            respuesta = 'Para cancelar, dime el código de 6 dígitos de la reserva. Ej: "cancelar 123456"'
        else:
            respuesta = 'No pudimos identificar tu perfil de estudiante.'
        accion_realizada = 'cancelar'

    # ========== Si no es keyword → va a n8n ==========
    if not respuesta:
        contexto_usuario = f'[Usuario: {nombre_completo} (Cédula: {cedula})] ' if cedula else f'[Usuario: {request.user.username}] '
        payload = {
            'chatInput': f'{contexto_usuario}{data.get("mensaje", "").strip()}',
            'sessionId': str(request.user.id),
        }

        try:
            resp = requests.post(settings.N8N_CHATBOT_WEBHOOK_URL, json=payload, timeout=20)
            resp.raise_for_status()
            resp_data = resp.json()
            respuesta = resp_data.get('output', '')
        except requests.RequestException:
            respuesta = 'El servicio de chat no está disponible. Intenta más tarde.'
        except (ValueError, KeyError, IndexError, TypeError):
            respuesta = 'Recibí una respuesta inválida del asistente.'

        if not respuesta:
            respuesta = 'No entendí tu mensaje. ¿Puedes intentar de otra forma?'

        # ========== Parsear JSON de acción desde la respuesta del AI ==========
        json_match = re.search(r'\{\s*"action"\s*:\s*"(reservar|cancelar|mis_reservas)"', respuesta)
        if json_match:
            try:
                block_start = respuesta.index('{', json_match.start())
                block_end = respuesta.index('}', block_start) + 1
                accion_data = json.loads(respuesta[block_start:block_end])
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
                        fecha_dt == timezone.localdate() and hora_inicio_dt <= timezone.localtime().time()
                    ):
                        respuesta = (
                            'Esa fecha u horario ya pasó. Reserva para hoy a una hora más tarde '
                            'o para otro día.'
                        )
                    elif vigentes >= 2:
                        respuesta = (
                            'Ya tienes 2 reservas activas. Espera a que se completen '
                            'o cancela alguna antes de reservar otra.'
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
                            f'✅ *¡Reserva creada!*\n'
                            f'👤 A nombre de: {nombre_completo}\n'
                            f'📅 Fecha: {fecha_uso}\n'
                            f'⏰ Horario: {hora_inicio} - {hora_fin}\n'
                            f'🔑 Código: *{codigo}*\n\n'
                            f'Presenta este código en el CRAI para confirmar tu reserva.'
                        )
                        accion_realizada = 'reservar'

                elif accion == 'cancelar' and estudiante:
                    codigo = accion_data.get('codigo', '')
                    if codigo:
                        try:
                            reserva = Reserva.objects.get(codigo_verificacion=codigo, estudiante=estudiante)
                            if reserva.estado in ('pendiente', 'confirmada'):
                                reserva.estado = 'cancelada'
                                reserva.save(update_fields=['estado'])
                                respuesta = f'✅ Reserva *{codigo}* cancelada con éxito.'
                            else:
                                respuesta = f'La reserva *{codigo}* ya está {reserva.get_estado_display()}.'
                        except Reserva.DoesNotExist:
                            respuesta = f'No encontramos una reserva con código *{codigo}* en tu cuenta.'
                    accion_realizada = 'cancelar'

                elif accion == 'mis_reservas' and estudiante:
                    reservas = Reserva.objects.filter(estudiante=estudiante).order_by('-fecha_uso')[:5]
                    if reservas:
                        lines = [f'📋 *Tus reservas ({nombre_completo})*']
                        emojis = {'pendiente': '⏳', 'confirmada': '✅', 'cancelada': '❌', 'completada': '✔️'}
                        for r in reservas:
                            e = emojis.get(r.estado, '❓')
                            lines.append(f'{e} *{r.codigo_verificacion}* — {r.fecha_uso} ({r.get_estado_display()})')
                        respuesta = '\n'.join(lines)
                    else:
                        respuesta = f'No tienes reservas, {nombre_completo}. ¿Quieres hacer una?'
                    accion_realizada = 'mis_reservas'

            except (ValueError, json.JSONDecodeError):
                pass

    # ========== Guardar conversación ==========
    ChatbotConversacion.objects.create(
        usuario=request.user,
        mensaje_usuario=data.get('mensaje', '').strip(),
        respuesta_bot=respuesta,
        canal='web',
        intencion_detectada=accion_realizada or 'conversacion',
    )

    return JsonResponse({
        'success': True,
        'respuesta': respuesta,
        'accion': accion_realizada,
    })


# ==========================================
# APIs DE CONSULTA PARA N8N
# ==========================================

def api_info_estudiante(request):
    """Devuelve datos del estudiante por cédula (para n8n)."""
    from apps.prestamos.models import Estudiante, Usuario as PerfilUsuario

    api_key = request.META.get('HTTP_X_N8N_KEY', '')
    if api_key != settings.N8N_API_KEY:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    cedula = request.GET.get('cedula', '').strip()
    if not cedula:
        return JsonResponse({'error': 'Parámetro cedula requerido'}, status=400)

    try:
        perfil = PerfilUsuario.objects.get(cedula=cedula)
        estudiante = Estudiante.objects.get(usuario=perfil)
    except (PerfilUsuario.DoesNotExist, Estudiante.DoesNotExist):
        return JsonResponse({'error': 'Estudiante no encontrado'}, status=404)

    return JsonResponse({
        'cedula': perfil.cedula,
        'nombres': perfil.user.first_name,
        'apellidos': perfil.user.last_name,
        'carrera': estudiante.carrera.nombre,
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
    fecha_uso = data.get('fecha_uso', '').strip()
    hora_inicio = data.get('hora_inicio', '08:00').strip()
    hora_fin = data.get('hora_fin', '').strip()
    motivo = data.get('motivo', '').strip()

    if not cedula:
        return JsonResponse({'error': 'Parámetro cedula requerido'}, status=400)
    if not fecha_uso:
        return JsonResponse({'error': 'Parámetro fecha_uso requerido'}, status=400)

    try:
        perfil = PerfilUsuario.objects.get(cedula=cedula)
        estudiante = Estudiante.objects.get(usuario=perfil)
    except (PerfilUsuario.DoesNotExist, Estudiante.DoesNotExist):
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

    vigentes = Reserva.objects.filter(
        estudiante=estudiante,
        estado__in=['pendiente', 'confirmada']
    ).count()
    if vigentes >= 2:
        return JsonResponse({'error': 'El estudiante ya tiene 2 reservas activas'}, status=400)

    fecha = datetime.strptime(fecha_uso, '%Y-%m-%d').date()

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

def api_disponibilidad(request):
    """Devuelve disponibilidad actual de Chromebooks (para n8n)."""
    from apps.prestamos.models import Chromebook

    api_key = request.META.get('HTTP_X_N8N_KEY', '')
    if api_key != settings.N8N_API_KEY:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    total = Chromebook.objects.count()
    disponibles = Chromebook.objects.filter(estado='disponible').count()
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

    cedula = request.GET.get('cedula', '')
    if not cedula:
        return JsonResponse({'error': 'Parámetro cedula requerido'}, status=400)

    try:
        perfil = PerfilUsuario.objects.get(cedula=cedula)
        estudiante = Estudiante.objects.get(usuario=perfil)
    except (PerfilUsuario.DoesNotExist, Estudiante.DoesNotExist):
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