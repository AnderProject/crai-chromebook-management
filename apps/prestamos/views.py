from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from .models import Chromebook, Prestamo, Estudiante, Usuario as PerfilUsuario
from django.utils import timezone
from datetime import datetime, timedelta, time
from django.conf import settings
import unicodedata
import json
import uuid
import os
import re

# Variable global temporal para guardar los tokens QR
qr_tokens = {}


@login_required
def portal(request):
    """Portal principal de módulos - Bienvenida"""
    contexto = {'titulo_pagina': 'Portal - CRAI UNEMI'}
    return render(request, 'prestamos/portal/portal.html', contexto)


CRAI_HORA_APERTURA = time(8, 0)
CRAI_HORA_CIERRE = time(17, 0)

# Máximo de reservas vigentes (pendiente/confirmada) que un estudiante puede tener.
MAX_RESERVAS_VIGENTES = 2


def _crai_abierto(ahora=None):
    """True si el CRAI está en horario de atención (08:00–17:00, hora del servidor)."""
    actual = (ahora or timezone.localtime()).time()
    return CRAI_HORA_APERTURA <= actual < CRAI_HORA_CIERRE


@login_required
def dashboard(request):
    """Vista principal del dashboard con datos reales"""
    from .models import Chromebook, Prestamo, Reserva, Notificacion

    _expirar_reservas_vencidas()

    # Obtener solo primer nombre y primer apellido
    primer_nombre = request.user.first_name.split()[0] if request.user.first_name else 'Admin'
    primer_apellido = request.user.last_name.split()[0] if request.user.last_name else 'CRAI'
    
    total_chromebooks = Chromebook.objects.count()
    disponibles = _disponibles_inventario()
    prestados = Chromebook.objects.filter(estado='prestado').count()
    en_mantenimiento = Chromebook.objects.filter(estado='mantenimiento').count()
    porcentaje_disponible = round((disponibles / total_chromebooks) * 100) if total_chromebooks > 0 else 0

    prestamos_activos = Prestamo.objects.filter(estado='activo').count()
    por_vencer = _reservas_por_vencer()
    vencidos = Prestamo.objects.filter(estado='vencido').count()
    
    total_estudiantes = User.objects.filter(groups__name='Estudiante').count()
    ultimos_prestamos = Prestamo.objects.select_related('estudiante', 'chromebook').all().order_by('-fecha_prestamo')[:5]
    notificaciones = Notificacion.objects.all().order_by('-fecha_envio')[:5]
    
    hoy = timezone.now().date()
    reservas_hoy = Reserva.objects.filter(fecha_uso=hoy, estado='pendiente').count()

    # Reservas aún sin procesar (equipos ya apartados por estudiantes), incluso futuras.
    reservas_pendientes = (
        Reserva.objects
        .filter(estado='pendiente')
        .select_related('estudiante__usuario__user', 'estudiante__carrera')
        .order_by('fecha_uso', 'hora_inicio')
    )

    contexto = {
        'titulo_pagina': 'Dashboard - CRAI UNEMI',
        'total_chromebooks': total_chromebooks,
        'disponibles': disponibles,
        'prestados': prestados,
        'en_mantenimiento': en_mantenimiento,
        'porcentaje_disponible': porcentaje_disponible,
        'prestamos_activos': prestamos_activos,
        'por_vencer': por_vencer,
        'vencidos': vencidos,
        'total_estudiantes': total_estudiantes,
        'ultimos_prestamos': ultimos_prestamos,
        'notificaciones': notificaciones,
        'total_notificaciones': Notificacion.objects.count(),
        'reservas_hoy': reservas_hoy,
        'reservas_pendientes': reservas_pendientes,
        'primer_nombre': primer_nombre,
        'primer_apellido': primer_apellido,
        'crai_abierto': _crai_abierto(),
        'crai_horario': f'{CRAI_HORA_APERTURA.strftime("%H:%M")} a {CRAI_HORA_CIERRE.strftime("%H:%M")}',
    }
    return render(request, 'prestamos/dashboard.html', contexto)


# ==========================================
# APIs DE ACTUALIZACIÓN EN VIVO (ADMIN, polling)
# ==========================================

@login_required
def api_dashboard_stats(request):
    """Contadores del dashboard + tabla de últimos préstamos (para refresco en vivo)."""
    from .models import Chromebook, Prestamo, Reserva

    _expirar_reservas_vencidas()

    total_chromebooks = Chromebook.objects.count()
    disponibles = _disponibles_inventario()
    prestados = Chromebook.objects.filter(estado='prestado').count()
    en_mantenimiento = Chromebook.objects.filter(estado='mantenimiento').count()
    porcentaje_disponible = round((disponibles / total_chromebooks) * 100) if total_chromebooks > 0 else 0

    prestamos_activos = Prestamo.objects.filter(estado='activo').count()
    por_vencer = _reservas_por_vencer()
    total_estudiantes = User.objects.filter(groups__name='Estudiante').count()
    reservas_hoy = Reserva.objects.filter(fecha_uso=timezone.now().date(), estado='pendiente').count()

    ultimos_prestamos = Prestamo.objects.select_related('estudiante', 'chromebook').all().order_by('-fecha_prestamo')[:5]
    filas_html = render_to_string('prestamos/partials/_ultimos_prestamos_rows.html', {'ultimos_prestamos': ultimos_prestamos})

    reservas_pendientes = (
        Reserva.objects
        .filter(estado='pendiente')
        .select_related('estudiante__usuario__user', 'estudiante__carrera')
        .order_by('fecha_uso', 'hora_inicio')
    )
    reservas_html = render_to_string('prestamos/partials/_reservas_pendientes_rows.html', {'reservas_pendientes': reservas_pendientes})

    return JsonResponse({
        'contadores': {
            'total_chromebooks': total_chromebooks,
            'disponibles': disponibles,
            'prestamos_activos': prestamos_activos,
            'por_vencer': por_vencer,
            'total_estudiantes': total_estudiantes,
            'reservas_hoy': reservas_hoy,
            'porcentaje_disponible': porcentaje_disponible,
            'reservas_pendientes': reservas_pendientes.count(),
        },
        'filas_html': filas_html,
        'reservas_html': reservas_html,
    })


@login_required
def api_prestamos_hoy(request):
    """Lista de préstamos de hoy + total (para refresco en vivo del registro rápido)."""
    _activar_reservas_pendientes()
    hoy = timezone.localtime().date()
    prestamos_hoy = Prestamo.objects.filter(
        fecha_prestamo__date=hoy
    ).select_related('estudiante', 'chromebook').order_by('-fecha_prestamo')
    total_hoy = prestamos_hoy.count()
    html = render_to_string('prestamos/partials/_prestamos_hoy.html', {'prestamos_hoy': prestamos_hoy})
    return JsonResponse({'html': html, 'total_hoy': total_hoy})


@login_required
def api_chromebooks_estado(request):
    """Contadores e inventario {codigo: estado} (para refresco en vivo de chromebooks)."""
    from .models import Chromebook

    chromebooks = list(Chromebook.objects.all())
    _marcar_pendiente_reserva(chromebooks)

    total = len(chromebooks)
    disponibles = sum(1 for cb in chromebooks if cb.estado_efectivo == 'disponible')
    prestados = sum(1 for cb in chromebooks if cb.estado_efectivo == 'prestado')
    en_mantenimiento = sum(1 for cb in chromebooks if cb.estado_efectivo == 'mantenimiento')
    pendiente_reserva = sum(1 for cb in chromebooks if cb.estado_efectivo == 'pendiente_reserva')
    estados = {cb.codigo: cb.estado_efectivo for cb in chromebooks}

    return JsonResponse({
        'contadores': {
            'total': total,
            'disponibles': disponibles,
            'prestados': prestados,
            'en_mantenimiento': en_mantenimiento,
            'pendiente_reserva': pendiente_reserva,
        },
        'estados': estados,
    })


@login_required
def api_monitoreo(request):
    """Listas de monitoreo de estudiantes (activos y vencidos) para refresco en vivo."""
    from .models import Reserva

    _expirar_reservas_vencidas()

    reservas_vencidas_lista = Reserva.objects.filter(estado='vencida').select_related(
        'estudiante__usuario__user', 'carrera'
    ).order_by('-fecha_uso', '-hora_inicio')[:10]
    prestamos_activos_lista = Prestamo.objects.filter(estado='activo').select_related(
        'estudiante', 'chromebook'
    ).order_by('fecha_devolucion')[:10]
    prestamos_vencidos_lista = Prestamo.objects.filter(estado='vencido').select_related(
        'estudiante', 'chromebook'
    ).order_by('-fecha_devolucion')[:10]

    activos_html = render_to_string('prestamos/partials/_monitoreo_activos.html', {
        'prestamos_activos_lista': prestamos_activos_lista,
    })
    vencidos_html = render_to_string('prestamos/partials/_monitoreo_vencidos.html', {
        'prestamos_vencidos_lista': prestamos_vencidos_lista,
        'reservas_vencidas_lista': reservas_vencidas_lista,
    })

    return JsonResponse({
        'activos_html': activos_html,
        'vencidos_html': vencidos_html,
        'count_activos': len(prestamos_activos_lista),
        'count_vencidos': len(prestamos_vencidos_lista) + len(reservas_vencidas_lista),
    })


@login_required
def api_reportes_temporal(request):
    """Serie temporal de préstamos según el rango (dia|semana|mes|anio). Para gráfico interactivo."""
    import calendar

    rango = request.GET.get('rango', 'semana')
    hoy = timezone.localdate()
    labels, data, etiqueta = [], [], 'Préstamos'

    if rango == 'dia':
        # Hoy, por hora (00:00 - 23:00)
        buckets = [0] * 24
        qs = Prestamo.objects.filter(fecha_prestamo__date=hoy)
        for p in qs:
            buckets[timezone.localtime(p.fecha_prestamo).hour] += 1
        labels = [f'{h:02d}:00' for h in range(24)]
        data = buckets

    elif rango == 'mes':
        # Días del mes actual
        ndias = calendar.monthrange(hoy.year, hoy.month)[1]
        buckets = {d: 0 for d in range(1, ndias + 1)}
        qs = Prestamo.objects.filter(fecha_prestamo__year=hoy.year, fecha_prestamo__month=hoy.month)
        for p in qs:
            buckets[timezone.localtime(p.fecha_prestamo).day] += 1
        labels = [str(d) for d in range(1, ndias + 1)]
        data = [buckets[d] for d in range(1, ndias + 1)]

    elif rango == 'anio':
        # 12 meses del año actual
        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        buckets = [0] * 12
        qs = Prestamo.objects.filter(fecha_prestamo__year=hoy.year)
        for p in qs:
            buckets[timezone.localtime(p.fecha_prestamo).month - 1] += 1
        labels = meses
        data = buckets

    else:  # semana: últimos 7 días
        rango = 'semana'
        dias = [hoy - timedelta(days=i) for i in range(6, -1, -1)]
        conteo = {d: 0 for d in dias}
        qs = Prestamo.objects.filter(fecha_prestamo__date__gte=dias[0], fecha_prestamo__date__lte=hoy)
        for p in qs:
            d = timezone.localtime(p.fecha_prestamo).date()
            if d in conteo:
                conteo[d] += 1
        labels = [d.strftime('%d/%m') for d in dias]
        data = [conteo[d] for d in dias]

    return JsonResponse({'rango': rango, 'labels': labels, 'data': data, 'etiqueta': etiqueta})


@csrf_exempt
def api_devolver_prestamo(request):
    """API para registrar la devolución de un Chromebook (con evidencia opcional)."""
    if request.method == 'POST':
        from .models import Evidencia
        from django.core.files import File

        data = json.loads(request.body)
        prestamo_id = data.get('prestamo_id')
        foto_nombre = data.get('foto_nombre', '')

        try:
            prestamo = Prestamo.objects.get(id=prestamo_id)

            if prestamo.estado != 'activo':
                return JsonResponse({'success': False, 'message': 'Este préstamo ya fue devuelto o está vencido.'})

            prestamo.fecha_devuelto = timezone.now()
            prestamo.estado = 'devuelto'
            prestamo.save()

            chromebook = prestamo.chromebook
            chromebook.estado = 'disponible'
            chromebook.save()

            # Si este préstamo venía de una reserva, marcarla como completada
            if prestamo.reserva:
                prestamo.reserva.estado = 'completada'
                prestamo.reserva.save()

            # Guardar evidencia de devolución si el admin tomó la foto.
            if foto_nombre:
                temp_path = os.path.join(settings.MEDIA_ROOT, 'evidencias', foto_nombre)
                if os.path.exists(temp_path):
                    evidencia = Evidencia.objects.create(prestamo=prestamo, tipo='devolucion', descripcion='Evidencia de devolución')
                    with open(temp_path, 'rb') as f:
                        evidencia.foto.save(foto_nombre, File(f), save=True)

            return JsonResponse({'success': True, 'message': f'{chromebook.codigo} devuelto exitosamente.'})

        except Prestamo.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Préstamo no encontrado.'})

    return JsonResponse({'success': False, 'message': 'Método no permitido'})


@csrf_exempt
def api_subir_evidencia(request):
    """Subir foto de evidencia antes de confirmar préstamo"""
    if request.method == 'POST' and request.FILES.get('foto'):
        return JsonResponse({'success': True, 'message': 'Foto subida'})
    return JsonResponse({'success': False})


@csrf_exempt
def api_generar_qr_evidencia(request):
    """Genera un token QR temporal para subir evidencia (entrega o devolución)."""
    if request.method == 'POST':
        data = json.loads(request.body)
        reserva_id = data.get('reserva_id')
        prestamo_id = data.get('prestamo_id')
        tipo = data.get('tipo', 'entrega')

        token = str(uuid.uuid4())[:8]

        qr_tokens[token] = {
            'reserva_id': reserva_id,
            'prestamo_id': prestamo_id,
            'tipo': tipo,
            'expiracion': timezone.now() + timedelta(minutes=2),
            'recibida': False
        }
        
        for key in list(qr_tokens.keys()):
            if qr_tokens[key]['expiracion'] < timezone.now():
                del qr_tokens[key]
        
        host = request.get_host()
        url_evidencia = f'https://{host}/prestamos/evidencia/{token}/'
        
        return JsonResponse({'success': True, 'token': token, 'url': url_evidencia})


def pagina_evidencia(request, token):
    """Página móvil para tomar foto de evidencia"""
    if token not in qr_tokens:
        return render(request, 'prestamos/evidencia/expirada.html')
    
    data = qr_tokens[token]
    
    if data['expiracion'] < timezone.now():
        del qr_tokens[token]
        return render(request, 'prestamos/evidencia/expirada.html')
    
    if request.method == 'POST' and request.FILES.get('foto'):
        foto = request.FILES['foto']
        reserva_id = data.get('reserva_id')
        prestamo_id = data.get('prestamo_id')

        try:
            if prestamo_id:
                # Evidencia de devolución: se nombra por estudiante + equipo + préstamo.
                from .models import Prestamo
                prestamo = Prestamo.objects.select_related('estudiante', 'chromebook').get(id=prestamo_id)
                nombre_completo = (prestamo.estudiante.get_full_name() or prestamo.estudiante.username).replace(' ', '_')
                nombre_estudiante = unicodedata.normalize('NFKD', nombre_completo).encode('ASCII', 'ignore').decode('ASCII')
                nombre_archivo = f'{nombre_estudiante}_DEV_{prestamo.chromebook.codigo}_{prestamo_id}.jpg'
            else:
                from .models import Reserva
                reserva = Reserva.objects.select_related('estudiante__usuario__user').get(id=reserva_id)
                nombre_completo = reserva.estudiante.usuario.user.get_full_name().replace(' ', '_')
                nombre_estudiante = unicodedata.normalize('NFKD', nombre_completo).encode('ASCII', 'ignore').decode('ASCII')
                codigo_reserva = reserva.codigo_verificacion
                nombre_archivo = f'{nombre_estudiante}_{codigo_reserva}.jpg'
        except:
            nombre_archivo = f'evidencia_{prestamo_id or reserva_id}_{token}.jpg'
        
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'evidencias')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, nombre_archivo)
        
        with open(temp_path, 'wb') as f:
            for chunk in foto.chunks():
                f.write(chunk)
        
        qr_tokens[token]['recibida'] = True
        qr_tokens[token]['foto_path'] = temp_path
        qr_tokens[token]['nombre_archivo'] = nombre_archivo
        
        print(f'✅ Foto guardada: {nombre_archivo}')
        
        response = render(request, 'prestamos/evidencia/exitosa.html')
        response['ngrok-skip-browser-warning'] = 'true'
        return response
    
    response = render(request, 'prestamos/evidencia/subir.html', {'token': token})
    response['ngrok-skip-browser-warning'] = 'true'
    return response


@csrf_exempt
def api_subir_evidencia_webcam(request):
    """Guarda una foto de evidencia capturada con la webcam del propio equipo.

    Recibe JSON: { reserva_id | prestamo_id, tipo, imagen (dataURL base64) }.
    Guarda en media/evidencias con la MISMA convención de nombres que el flujo QR
    y devuelve nombre_archivo, para que confirmar_prestamo/devolución lo reutilicen.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    import base64

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'JSON inválido'}, status=400)

    reserva_id = data.get('reserva_id')
    prestamo_id = data.get('prestamo_id')
    temp_key = data.get('temp_key')   # préstamo inmediato: aún no existe el Prestamo
    imagen = data.get('imagen', '')

    if not imagen:
        return JsonResponse({'success': False, 'message': 'No se recibió la imagen.'})
    if ',' in imagen:
        imagen = imagen.split(',', 1)[1]
    try:
        binario = base64.b64decode(imagen)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Imagen inválida.'})

    # Mismo nombre de archivo que en pagina_evidencia (flujo QR)
    try:
        if temp_key and not prestamo_id and not reserva_id:
            # Foto previa al registro: nombre temporal determinista (se reusa al recapturar)
            clave = re.sub(r'[^A-Za-z0-9_-]', '', str(temp_key))
            nombre_archivo = f'temp_entrega_{clave}.jpg'
        elif prestamo_id:
            prestamo = Prestamo.objects.select_related('estudiante', 'chromebook').get(id=prestamo_id)
            nombre_completo = (prestamo.estudiante.get_full_name() or prestamo.estudiante.username).replace(' ', '_')
            nombre_estudiante = unicodedata.normalize('NFKD', nombre_completo).encode('ASCII', 'ignore').decode('ASCII')
            nombre_archivo = f'{nombre_estudiante}_DEV_{prestamo.chromebook.codigo}_{prestamo_id}.jpg'
        else:
            from .models import Reserva
            reserva = Reserva.objects.select_related('estudiante__usuario__user').get(id=reserva_id)
            nombre_completo = reserva.estudiante.usuario.user.get_full_name().replace(' ', '_')
            nombre_estudiante = unicodedata.normalize('NFKD', nombre_completo).encode('ASCII', 'ignore').decode('ASCII')
            nombre_archivo = f'{nombre_estudiante}_{reserva.codigo_verificacion}.jpg'
    except Exception:
        nombre_archivo = f'evidencia_webcam_{prestamo_id or reserva_id}.jpg'

    temp_dir = os.path.join(settings.MEDIA_ROOT, 'evidencias')
    os.makedirs(temp_dir, exist_ok=True)
    with open(os.path.join(temp_dir, nombre_archivo), 'wb') as f:
        f.write(binario)

    return JsonResponse({'success': True, 'nombre_archivo': nombre_archivo})


@login_required
@login_required
@csrf_exempt
def api_toggle_matriculas(request):
    """Conecta/desconecta la integración con la API de matrículas (flag global)."""
    from .models import ConfiguracionSistema
    config = ConfiguracionSistema.obtener()
    if request.method == 'POST':
        config.api_matriculas_activa = not config.api_matriculas_activa
        config.save(update_fields=['api_matriculas_activa', 'actualizado'])
    return JsonResponse({'success': True, 'activa': config.api_matriculas_activa})


def api_test_conexion(request):
    """Prueba la conexión con la API de matrículas"""
    import requests
    from .models import ConfiguracionSistema
    if not ConfiguracionSistema.obtener().api_matriculas_activa:
        return JsonResponse({
            'success': False,
            'desconectada': True,
            'message': 'La API de matrículas está desconectada. Actívala para probar la conexión.',
        })
    try:
        url = f'{settings.API_MATRICULAS_BASE_URL.rstrip("/")}/'
        resp = requests.get(
            url,
            headers={'X-API-KEY': settings.API_MATRICULAS_KEY},
            timeout=settings.API_MATRICULAS_TIMEOUT,
        )
        return JsonResponse({
            'success': True,
            'message': 'Conexión exitosa con la API de matrículas',
            'status_code': resp.status_code,
            'base_url': settings.API_MATRICULAS_BASE_URL,
        })
    except requests.RequestException as e:
        return JsonResponse({
            'success': False,
            'message': f'No se pudo conectar: {str(e)}',
            'base_url': settings.API_MATRICULAS_BASE_URL,
        })


@login_required
def api_sincronizar_estudiantes(request):
    """Sincroniza todos los estudiantes desde la API de matrículas"""
    from .services.api_estudiantes import listar_estudiantes, ApiEstudiantesError
    from .services.sincronizacion import sincronizar_estudiante
    from .models import ConfiguracionSistema

    if not ConfiguracionSistema.obtener().api_matriculas_activa:
        return JsonResponse({
            'success': False,
            'desconectada': True,
            'message': 'La API de matrículas está desconectada. Actívala para sincronizar.',
        })

    try:
        estudiantes = listar_estudiantes()
    except ApiEstudiantesError as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al conectar con API de matrículas: {str(e)}',
        })

    creados = actualizados = errores = 0
    for data in estudiantes:
        try:
            _, creado = sincronizar_estudiante(data)
            if creado:
                creados += 1
            else:
                actualizados += 1
        except Exception:
            errores += 1

    return JsonResponse({
        'success': True,
        'message': f'Sincronización completada. Creados: {creados}, Actualizados: {actualizados}, Errores: {errores}.',
        'creados': creados,
        'actualizados': actualizados,
        'errores': errores,
        'total': len(estudiantes),
    })


@login_required
def reportes(request):
    """Panel de reportes (Fase 1).

    Organiza los datos en 5 categorías que la plantilla muestra en pestañas:
      - KPIs principales (6 indicadores)
      - Temporal: préstamos por mes/semana, horas pico y día de la semana
      - Distribución: por carrera, semestre, facultad, marca, condición e inventario
      - Estudiantes: rankings (top, con vencidos, cumplidos, nuevos)
      - Mantenimiento: por mes, tipo, costo, tiempo de reparación y técnicos
      - Operativo: tablas de préstamos activos, vencidos, por vencer y devueltos hoy
    """
    from .models import Chromebook, Prestamo, Mantenimiento, Notificacion
    from django.db.models import Count, Sum, Avg, Q, F, ExpressionWrapper, DurationField
    from django.db.models.functions import TruncMonth, TruncWeek, ExtractHour, ExtractWeekDay

    # Solo administradores/TICs pueden ver los reportes; los recepcionistas no.
    if not (request.user.is_superuser or
            request.user.groups.filter(name__in=['Administrador', 'Tics']).exists()):
        return redirect('prestamos:dashboard')

    MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    tz = timezone.get_current_timezone()
    ahora = timezone.now()
    hoy = timezone.localdate()

    # Encabezado (mismo patrón que el dashboard)
    primer_nombre = request.user.first_name.split()[0] if request.user.first_name else 'Admin'
    primer_apellido = request.user.last_name.split()[0] if request.user.last_name else 'CRAI'

    # Ruta de relación Prestamo -> Estudiante (User -> perfil -> estudiante)
    EST = 'estudiante__perfil__estudiante'

    # =====================================================================
    # KPIs PRINCIPALES (6)
    # =====================================================================
    total_prestamos = Prestamo.objects.count()
    prestamos_hoy = Prestamo.objects.filter(fecha_prestamo__date=hoy).count()

    vencidos = Prestamo.objects.filter(estado='vencido').count()
    tasa_vencimiento = round(vencidos / total_prestamos * 100) if total_prestamos else 0

    # % de devoluciones a tiempo (reemplaza una "calificación": usa dato real)
    devueltos = Prestamo.objects.filter(fecha_devuelto__isnull=False)
    total_devueltos = devueltos.count()
    a_tiempo = devueltos.filter(fecha_devuelto__lte=F('fecha_devolucion')).count()
    pct_a_tiempo = round(a_tiempo / total_devueltos * 100) if total_devueltos else 0

    # Tasa de reincidencia: estudiantes que pidieron 2+ veces / estudiantes que pidieron
    con_prestamo = User.objects.annotate(n=Count('prestamo')).filter(n__gt=0)
    total_con_prestamo = con_prestamo.count()
    repiten = con_prestamo.filter(n__gte=2).count()
    tasa_reincidencia = round(repiten / total_con_prestamo * 100) if total_con_prestamo else 0

    # Tiempo promedio real por préstamo (horas), sobre los devueltos
    prom = (
        devueltos
        .annotate(dur=ExpressionWrapper(F('fecha_devuelto') - F('fecha_prestamo'),
                                        output_field=DurationField()))
        .aggregate(p=Avg('dur'))['p']
    )
    tiempo_promedio = round(prom.total_seconds() / 3600, 1) if prom else 0

    # =====================================================================
    # TEMPORAL
    # =====================================================================
    # Por mes (últimos 6 meses)
    hace_6_meses = ahora - timedelta(days=180)
    por_mes = (
        Prestamo.objects.filter(fecha_prestamo__gte=hace_6_meses)
        .annotate(mes=TruncMonth('fecha_prestamo')).values('mes')
        .annotate(total=Count('id')).order_by('mes')
    )
    mes_labels = [f'{MESES_ES[p["mes"].month - 1]} {p["mes"].year}' for p in por_mes]
    mes_data = [p['total'] for p in por_mes]

    # Por semana (últimas 8 semanas)
    hace_8_semanas = ahora - timedelta(weeks=8)
    por_semana = (
        Prestamo.objects.filter(fecha_prestamo__gte=hace_8_semanas)
        .annotate(sem=TruncWeek('fecha_prestamo')).values('sem')
        .annotate(total=Count('id')).order_by('sem')
    )
    semana_labels = [p['sem'].strftime('%d/%m') for p in por_semana]
    semana_data = [p['total'] for p in por_semana]

    # Horas pico (jornada 7:00 a 21:00)
    horas_qs = (
        Prestamo.objects
        .annotate(h=ExtractHour('fecha_prestamo', tzinfo=tz))
        .values('h').annotate(total=Count('id'))
    )
    horas_map = {h['h']: h['total'] for h in horas_qs}
    horas_rango = list(range(7, 22))
    hora_labels = [f'{h:02d}:00' for h in horas_rango]
    hora_data = [horas_map.get(h, 0) for h in horas_rango]

    # Día de la semana (ExtractWeekDay: 1=domingo ... 7=sábado)
    dia_qs = (
        Prestamo.objects
        .annotate(d=ExtractWeekDay('fecha_prestamo', tzinfo=tz))
        .values('d').annotate(total=Count('id'))
    )
    dia_map = {d['d']: d['total'] for d in dia_qs}
    dia_orden = [2, 3, 4, 5, 6, 7, 1]  # Lun..Dom
    dia_labels = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    dia_data = [dia_map.get(d, 0) for d in dia_orden]

    # =====================================================================
    # DISTRIBUCIÓN
    # =====================================================================
    total_chromebooks = Chromebook.objects.count()
    inventario = {'disponible': 0, 'prestado': 0, 'mantenimiento': 0}
    for fila in Chromebook.objects.values('estado').annotate(total=Count('id')):
        inventario[fila['estado']] = fila['total']

    condicion = {'bueno': 0, 'regular': 0, 'malo': 0}
    for fila in Chromebook.objects.values('condicion').annotate(total=Count('id')):
        condicion[fila['condicion']] = fila['total']

    def _distribucion(campo, limite=None, ordenar_por_total=True):
        qs = (
            Prestamo.objects.filter(**{f'{campo}__isnull': False})
            .values(campo).annotate(total=Count('id'))
        )
        qs = qs.order_by('-total') if ordenar_por_total else qs.order_by(campo)
        if limite:
            qs = qs[:limite]
        return qs

    carrera_qs = _distribucion(f'{EST}__carrera__nombre', limite=8)
    carrera_labels = [c[f'{EST}__carrera__nombre'] for c in carrera_qs]
    carrera_data = [c['total'] for c in carrera_qs]

    semestre_qs = _distribucion(f'{EST}__semestre', ordenar_por_total=False)
    semestre_labels = [f'Sem {c[f"{EST}__semestre"]}' for c in semestre_qs]
    semestre_data = [c['total'] for c in semestre_qs]

    facultad_qs = _distribucion(f'{EST}__carrera__facultad__nombre', limite=8)
    facultad_labels = [c[f'{EST}__carrera__facultad__nombre'] for c in facultad_qs]
    facultad_data = [c['total'] for c in facultad_qs]

    marca_qs = _distribucion('chromebook__marca')
    marca_labels = [c['chromebook__marca'] for c in marca_qs]
    marca_data = [c['total'] for c in marca_qs]

    # =====================================================================
    # ESTUDIANTES (rankings)
    # =====================================================================
    def _nombre(u):
        return u.get_full_name() or u.username

    def _cedula(u):
        perfil = getattr(u, 'perfil', None)
        return perfil.cedula if perfil else '—'

    top_estudiantes = (
        User.objects.filter(groups__name='Estudiante')
        .annotate(n=Count('prestamo')).filter(n__gt=0)
        .select_related('perfil').order_by('-n')[:10]
    )
    tabla_top = [{'nombre': _nombre(u), 'cedula': _cedula(u), 'total': u.n}
                 for u in top_estudiantes]

    con_vencidos = (
        User.objects
        .annotate(nv=Count('prestamo', filter=Q(prestamo__estado='vencido')))
        .filter(nv__gt=0).select_related('perfil').order_by('-nv')[:10]
    )
    tabla_vencidos_est = [{'nombre': _nombre(u), 'cedula': _cedula(u), 'total': u.nv}
                          for u in con_vencidos]

    cumplidos = (
        User.objects
        .annotate(
            dev=Count('prestamo', filter=Q(prestamo__fecha_devuelto__isnull=False)),
            at=Count('prestamo', filter=Q(prestamo__fecha_devuelto__isnull=False,
                                          prestamo__fecha_devuelto__lte=F('prestamo__fecha_devolucion'))),
            venc=Count('prestamo', filter=Q(prestamo__estado='vencido')),
        )
        .filter(dev__gt=0, venc=0).select_related('perfil').order_by('-at')[:10]
    )
    tabla_cumplidos = [
        {'nombre': _nombre(u), 'cedula': _cedula(u), 'total': u.dev,
         'pct': round(u.at / u.dev * 100) if u.dev else 0}
        for u in cumplidos
    ]

    hace_30 = ahora - timedelta(days=30)
    nuevos = (
        User.objects.filter(groups__name='Estudiante', date_joined__gte=hace_30)
        .select_related('perfil').order_by('-date_joined')[:10]
    )
    tabla_nuevos = [{'nombre': _nombre(u), 'cedula': _cedula(u), 'fecha': u.date_joined}
                    for u in nuevos]

    # =====================================================================
    # MANTENIMIENTO
    # =====================================================================
    total_mantenimientos = Mantenimiento.objects.count()
    costo_total = Mantenimiento.objects.aggregate(t=Sum('costo'))['t'] or 0

    mant_mes_qs = (
        Mantenimiento.objects.filter(fecha_inicio__gte=hace_6_meses.date())
        .annotate(mes=TruncMonth('fecha_inicio')).values('mes')
        .annotate(total=Count('id')).order_by('mes')
    )
    mant_mes_labels = [f'{MESES_ES[m["mes"].month - 1]} {m["mes"].year}' for m in mant_mes_qs]
    mant_mes_data = [m['total'] for m in mant_mes_qs]

    mant_por_tipo = {'preventivo': 0, 'correctivo': 0}
    for fila in Mantenimiento.objects.values('tipo').annotate(total=Count('id')):
        mant_por_tipo[fila['tipo']] = fila['total']

    # Tiempo promedio de reparación (días) sobre mantenimientos finalizados
    prom_rep = (
        Mantenimiento.objects.filter(fecha_fin__isnull=False)
        .annotate(dur=ExpressionWrapper(F('fecha_fin') - F('fecha_inicio'),
                                        output_field=DurationField()))
        .aggregate(p=Avg('dur'))['p']
    )
    tiempo_reparacion = round(prom_rep.total_seconds() / 86400, 1) if prom_rep else 0

    tecnicos_qs = (
        Mantenimiento.objects.exclude(tecnico__isnull=True).exclude(tecnico='')
        .values('tecnico').annotate(n=Count('id'), costo=Sum('costo')).order_by('-n')[:10]
    )
    tabla_tecnicos = [{'tecnico': t['tecnico'], 'total': t['n'], 'costo': t['costo'] or 0}
                      for t in tecnicos_qs]

    # =====================================================================
    # OPERATIVO (tablas en tiempo real)
    # =====================================================================
    activos = (
        Prestamo.objects.filter(estado='activo')
        .select_related('estudiante', 'chromebook').order_by('fecha_devolucion')[:50]
    )

    vencidos_qs = (
        Prestamo.objects.filter(estado='vencido')
        .select_related('estudiante', 'chromebook').order_by('fecha_devolucion')[:50]
    )
    tabla_operativo_vencidos = []
    for p in vencidos_qs:
        atraso = ahora - p.fecha_devolucion
        tabla_operativo_vencidos.append({'p': p, 'horas': int(atraso.total_seconds() // 3600)})

    por_vencer = (
        Prestamo.objects.filter(estado='activo',
                                fecha_devolucion__gte=ahora,
                                fecha_devolucion__lte=ahora + timedelta(hours=24))
        .select_related('estudiante', 'chromebook').order_by('fecha_devolucion')[:50]
    )

    devueltos_hoy = (
        Prestamo.objects.filter(estado='devuelto', fecha_devuelto__date=hoy)
        .select_related('estudiante', 'chromebook').order_by('-fecha_devuelto')[:50]
    )

    # Notificaciones para el navbar (igual que el dashboard)
    notificaciones = Notificacion.objects.all().order_by('-fecha_envio')[:5]

    contexto = {
        'primer_nombre': primer_nombre,
        'primer_apellido': primer_apellido,
        'notificaciones': notificaciones,
        'total_notificaciones': Notificacion.objects.count(),

        # ---- KPIs ----
        'total_prestamos': total_prestamos,
        'prestamos_hoy': prestamos_hoy,
        'tasa_vencimiento': tasa_vencimiento,
        'pct_a_tiempo': pct_a_tiempo,
        'tasa_reincidencia': tasa_reincidencia,
        'tiempo_promedio': tiempo_promedio,

        # ---- Mantenimiento (stats) ----
        'total_mantenimientos': total_mantenimientos,
        'costo_total': costo_total,
        'tiempo_reparacion': tiempo_reparacion,

        # ---- Tablas (render en servidor) ----
        'tabla_top': tabla_top,
        'tabla_vencidos_est': tabla_vencidos_est,
        'tabla_cumplidos': tabla_cumplidos,
        'tabla_nuevos': tabla_nuevos,
        'tabla_tecnicos': tabla_tecnicos,
        'op_activos': activos,
        'op_vencidos': tabla_operativo_vencidos,
        'op_por_vencer': por_vencer,
        'op_devueltos_hoy': devueltos_hoy,

        # ---- Datos para gráficos (json_script) ----
        'mes_labels': mes_labels, 'mes_data': mes_data,
        'semana_labels': semana_labels, 'semana_data': semana_data,
        'hora_labels': hora_labels, 'hora_data': hora_data,
        'dia_labels': dia_labels, 'dia_data': dia_data,
        'inventario_data': [inventario['disponible'], inventario['prestado'], inventario['mantenimiento']],
        'condicion_data': [condicion['bueno'], condicion['regular'], condicion['malo']],
        'carrera_labels': carrera_labels, 'carrera_data': carrera_data,
        'semestre_labels': semestre_labels, 'semestre_data': semestre_data,
        'facultad_labels': facultad_labels, 'facultad_data': facultad_data,
        'marca_labels': marca_labels, 'marca_data': marca_data,
        'mant_mes_labels': mant_mes_labels, 'mant_mes_data': mant_mes_data,
        'mant_tipo_data': [mant_por_tipo['preventivo'], mant_por_tipo['correctivo']],
    }
    return render(request, 'prestamos/reportes/reportes.html', contexto)


def exportar_reportes(request):
    """Exporta los datos del panel de Reportes a CSV.

    Genera un ZIP con un CSV por cada tabla/gráfico que se ve en pantalla
    (temporal, distribución, rankings de estudiantes, mantenimiento y
    operativo). Cada CSV lleva BOM UTF-8 para que Excel respete los acentos.
    Reaprovecha exactamente las mismas consultas que la vista `reportes`.
    """
    import csv
    import io
    import zipfile
    from django.http import HttpResponse
    from .models import Chromebook, Prestamo, Mantenimiento
    from django.db.models import Count, Sum, Q, F

    if not (request.user.is_superuser or
            request.user.groups.filter(name__in=['Administrador', 'Tics']).exists()):
        return redirect('prestamos:dashboard')

    ahora = timezone.now()
    hoy = timezone.localdate()
    EST = 'estudiante__perfil__estudiante'

    def _nombre(u):
        return u.get_full_name() or u.username

    def _cedula(u):
        perfil = getattr(u, 'perfil', None)
        return perfil.cedula if perfil else '—'

    # (nombre_archivo, [encabezados], [filas]) por cada hoja de datos.
    hojas = []

    # ---- Resumen (KPIs) ----
    total_prestamos = Prestamo.objects.count()
    vencidos = Prestamo.objects.filter(estado='vencido').count()
    devueltos = Prestamo.objects.filter(fecha_devuelto__isnull=False)
    total_dev = devueltos.count()
    a_tiempo = devueltos.filter(fecha_devuelto__lte=F('fecha_devolucion')).count()
    hojas.append(('resumen.csv', ['Indicador', 'Valor'], [
        ['Préstamos totales', total_prestamos],
        ['Préstamos hoy', Prestamo.objects.filter(fecha_prestamo__date=hoy).count()],
        ['Préstamos vencidos', vencidos],
        ['Tasa de vencimiento (%)', round(vencidos / total_prestamos * 100) if total_prestamos else 0],
        ['Devoluciones a tiempo (%)', round(a_tiempo / total_dev * 100) if total_dev else 0],
    ]))

    # ---- Préstamos por carrera / semestre / facultad / marca ----
    def _dist(campo, etiqueta):
        filas = (
            Prestamo.objects.filter(**{f'{campo}__isnull': False})
            .values(campo).annotate(total=Count('id')).order_by('-total')
        )
        return ([etiqueta, 'Préstamos'], [[f[campo], f['total']] for f in filas])

    enc, filas = _dist(f'{EST}__carrera__nombre', 'Carrera')
    hojas.append(('prestamos_por_carrera.csv', enc, filas))
    enc, filas = _dist(f'{EST}__carrera__facultad__nombre', 'Facultad')
    hojas.append(('prestamos_por_facultad.csv', enc, filas))
    enc, filas = _dist('chromebook__marca', 'Marca')
    hojas.append(('prestamos_por_marca.csv', enc, filas))

    # ---- Inventario y condición ----
    inv = {'disponible': 0, 'prestado': 0, 'reservado': 0, 'mantenimiento': 0}
    for f in Chromebook.objects.values('estado').annotate(t=Count('id')):
        inv[f['estado']] = f['t']
    hojas.append(('inventario.csv', ['Estado', 'Equipos'],
                  [[k.title(), v] for k, v in inv.items()]))

    cond = {'bueno': 0, 'regular': 0, 'malo': 0}
    for f in Chromebook.objects.values('condicion').annotate(t=Count('id')):
        cond[f['condicion']] = f['t']
    hojas.append(('condicion_equipos.csv', ['Condición', 'Equipos'],
                  [[k.title(), v] for k, v in cond.items()]))

    # ---- Rankings de estudiantes ----
    top = (User.objects.filter(groups__name='Estudiante')
           .annotate(n=Count('prestamo')).filter(n__gt=0)
           .select_related('perfil').order_by('-n')[:10])
    hojas.append(('top_estudiantes.csv', ['Estudiante', 'Cédula', 'Préstamos'],
                  [[_nombre(u), _cedula(u), u.n] for u in top]))

    con_venc = (User.objects
                .annotate(nv=Count('prestamo', filter=Q(prestamo__estado='vencido')))
                .filter(nv__gt=0).select_related('perfil').order_by('-nv')[:10])
    hojas.append(('estudiantes_con_vencidos.csv', ['Estudiante', 'Cédula', 'Vencidos'],
                  [[_nombre(u), _cedula(u), u.nv] for u in con_venc]))

    # ---- Mantenimiento: técnicos ----
    tecnicos = (Mantenimiento.objects.exclude(tecnico__isnull=True).exclude(tecnico='')
                .values('tecnico').annotate(n=Count('id'), costo=Sum('costo')).order_by('-n')[:10])
    hojas.append(('mantenimiento_tecnicos.csv', ['Técnico', 'Trabajos', 'Costo total'],
                  [[t['tecnico'], t['n'], t['costo'] or 0] for t in tecnicos]))

    # ---- Operativo: préstamos activos y vencidos ----
    activos = (Prestamo.objects.filter(estado='activo')
               .select_related('estudiante', 'chromebook').order_by('fecha_devolucion'))
    hojas.append(('operativo_activos.csv',
                  ['Estudiante', 'Chromebook', 'Prestado', 'Devolución prevista'],
                  [[_nombre(p.estudiante), p.chromebook.codigo,
                    timezone.localtime(p.fecha_prestamo).strftime('%d/%m/%Y %H:%M'),
                    timezone.localtime(p.fecha_devolucion).strftime('%d/%m/%Y %H:%M')]
                   for p in activos]))

    venc = (Prestamo.objects.filter(estado='vencido')
            .select_related('estudiante', 'chromebook').order_by('fecha_devolucion'))
    filas_venc = []
    for p in venc:
        horas = int((ahora - p.fecha_devolucion).total_seconds() // 3600)
        filas_venc.append([_nombre(p.estudiante), p.chromebook.codigo,
                           timezone.localtime(p.fecha_devolucion).strftime('%d/%m/%Y %H:%M'),
                           horas])
    hojas.append(('operativo_vencidos.csv',
                  ['Estudiante', 'Chromebook', 'Vencía', 'Horas de atraso'], filas_venc))

    # ---- Empaquetar en ZIP ----
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for nombre, encabezados, filas in hojas:
            texto = io.StringIO()
            writer = csv.writer(texto)
            writer.writerow(encabezados)
            writer.writerows(filas)
            # BOM para que Excel reconozca UTF-8 y muestre bien los acentos.
            zf.writestr(nombre, '﻿' + texto.getvalue())

    buffer.seek(0)
    nombre_zip = f'reportes_crai_{hoy.strftime("%Y%m%d")}.zip'
    respuesta = HttpResponse(buffer.getvalue(), content_type='application/zip')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre_zip}"'
    return respuesta


def servir_evidencia(request, nombre_archivo):
    """Sirve la imagen de evidencia"""
    ruta = os.path.join(settings.MEDIA_ROOT, 'evidencias', nombre_archivo)
    if os.path.exists(ruta):
        return FileResponse(open(ruta, 'rb'), content_type='image/jpeg')
    return JsonResponse({'error': 'No encontrada'}, status=404)


@csrf_exempt
def api_verificar_evidencia(request):
    """Verifica si ya se subió la evidencia desde el celular"""
    if request.method == 'POST':
        data = json.loads(request.body)
        token = data.get('token')
        
        recibida = False
        nombre_archivo = None
        
        if token in qr_tokens:
            recibida = qr_tokens[token].get('recibida', False)
            nombre_archivo = qr_tokens[token].get('nombre_archivo', None)
        
        return JsonResponse({'success': True, 'recibida': recibida, 'nombre_archivo': nombre_archivo})


@csrf_exempt
def api_detalle_prestamo(request, id):
    """API para obtener detalles de un préstamo"""
    from .models import Evidencia
    
    try:
        prestamo = Prestamo.objects.select_related('estudiante', 'chromebook').get(id=id)
        
        evidencias = Evidencia.objects.filter(prestamo=prestamo)
        foto_url = None
        for ev in evidencias:
            if ev.foto:
                foto_url = ev.foto.url
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': f'#{prestamo.id:03d}',
                'estudiante': prestamo.estudiante.get_full_name() or prestamo.estudiante.username,
                'chromebook': prestamo.chromebook.codigo,
                'fecha_prestamo': prestamo.fecha_prestamo.strftime('%d/%m/%Y %H:%M'),
                'devolucion': prestamo.fecha_devuelto.strftime('%d/%m/%Y %H:%M') if prestamo.fecha_devuelto else (prestamo.fecha_devolucion.strftime('%d/%m/%Y %H:%M') if prestamo.fecha_devolucion else 'Pendiente'),
                'estado': prestamo.estado,
                'foto_url': foto_url,
            }
        })
    except Prestamo.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Préstamo no encontrado'})


@login_required
def lista_chromebooks(request):
    """Vista de inventario de Chromebooks con datos reales"""
    chromebooks = list(Chromebook.objects.all().order_by('codigo'))
    _marcar_pendiente_reserva(chromebooks)

    total = len(chromebooks)
    disponibles = sum(1 for cb in chromebooks if cb.estado_efectivo == 'disponible')
    prestados = sum(1 for cb in chromebooks if cb.estado_efectivo == 'prestado')
    en_mantenimiento = sum(1 for cb in chromebooks if cb.estado_efectivo == 'mantenimiento')
    pendiente_reserva = sum(1 for cb in chromebooks if cb.estado_efectivo == 'pendiente_reserva')

    contexto = {
        'titulo_pagina': 'Chromebooks - CRAI UNEMI',
        'chromebooks': chromebooks, 'total': total,
        'disponibles': disponibles, 'prestados': prestados,
        'en_mantenimiento': en_mantenimiento,
        'pendiente_reserva': pendiente_reserva,
    }
    return render(request, 'prestamos/chromebooks/lista.html', contexto)


def _marcar_pendiente_reserva(chromebooks):
    """Asigna ``estado_efectivo`` a cada Chromebook de la lista.

    Una reserva pendiente no aparta un equipo concreto, solo consume un cupo del día.
    Para reflejarlo en el inventario, marcamos como 'pendiente_reserva' tantos equipos
    'disponible' como reservas pendientes vigentes existan (de cualquier fecha). El resto
    conserva su estado real. Devuelve el nº de equipos marcados.
    """
    from .models import Reserva

    _expirar_reservas_vencidas()
    n_reservas = Reserva.objects.filter(estado='pendiente').count()

    for cb in chromebooks:
        cb.estado_efectivo = cb.estado

    libres = [cb for cb in chromebooks if cb.estado == 'disponible']
    marcar = min(n_reservas, len(libres))
    for cb in libres[:marcar]:
        cb.estado_efectivo = 'pendiente_reserva'
    return marcar


@login_required
def detalle_chromebook(request, pk):
    contexto = {'titulo_pagina': 'Detalle Chromebook - CRAI UNEMI'}
    return render(request, 'prestamos/chromebooks/detalle.html', contexto)


@login_required
def agregar_chromebook(request):
    from .forms import ChromebookForm
    from django.contrib import messages
    
    if request.method == 'POST':
        form = ChromebookForm(request.POST, request.FILES)  # ← AGREGAR request.FILES
        if form.is_valid():
            form.save()
            messages.success(request, 'Chromebook registrado exitosamente.')
            return redirect('prestamos:lista_chromebooks')
    else:
        form = ChromebookForm()
    
    return render(request, 'prestamos/chromebooks/agregar.html', {'titulo_pagina': 'Agregar Chromebook - CRAI UNEMI', 'form': form})



@login_required
def lista_mantenimientos(request):
    """Lista de equipos en mantenimiento"""
    from .models import Mantenimiento
    
    mantenimientos = Mantenimiento.objects.select_related('chromebook', 'registrado_por').all().order_by('-fecha_inicio')
    
    en_proceso = mantenimientos.filter(estado='en_proceso').count()
    finalizados = mantenimientos.filter(estado='finalizado').count()
    
    contexto = {
        'titulo_pagina': 'Mantenimiento - CRAI UNEMI',
        'mantenimientos': mantenimientos,
        'en_proceso': en_proceso,
        'finalizados': finalizados,
        'total': mantenimientos.count(),
    }
    return render(request, 'prestamos/mantenimiento/lista.html', contexto)


@login_required
def agregar_mantenimiento(request):
    """Formulario para registrar un nuevo mantenimiento"""
    from .models import Chromebook
    from django.contrib import messages
    
    if request.method == 'POST':
        chromebook_id = request.POST.get('chromebook_id')
        tipo = request.POST.get('tipo')
        descripcion_problema = request.POST.get('descripcion_problema')
        tecnico = request.POST.get('tecnico')
        costo = request.POST.get('costo', 0)
        en_garantia = request.POST.get('en_garantia') == '1'
        fecha_inicio = request.POST.get('fecha_inicio')

        try:
            chromebook = Chromebook.objects.get(id=chromebook_id)

            # Crear mantenimiento
            from .models import Mantenimiento
            Mantenimiento.objects.create(
                chromebook=chromebook,
                tipo=tipo,
                descripcion_problema=descripcion_problema,
                tecnico=tecnico,
                costo=costo,
                en_garantia=en_garantia,
                fecha_inicio=fecha_inicio,
                estado='en_proceso',
                registrado_por=request.user
            )
            
            # Actualizar estado y condición del Chromebook.
            # Correctivo = algo se dañó -> 'malo'; Preventivo = revisión -> 'regular'.
            # Al finalizar el mantenimiento la condición vuelve a 'bueno'.
            chromebook.estado = 'mantenimiento'
            chromebook.condicion = 'malo' if tipo == 'correctivo' else 'regular'
            chromebook.save()
            
            messages.success(request, f'{chromebook.codigo} enviado a mantenimiento.')
            return redirect('prestamos:lista_mantenimientos')
            
        except Chromebook.DoesNotExist:
            messages.error(request, 'Chromebook no encontrado.')
    
    chromebooks = Chromebook.objects.filter(estado__in=['disponible', 'prestado'])
    
    contexto = {
        'titulo_pagina': 'Agregar Mantenimiento - CRAI UNEMI',
        'chromebooks': chromebooks,
    }
    return render(request, 'prestamos/mantenimiento/agregar.html', contexto)


@csrf_exempt
def api_detalle_mantenimiento(request, id):
    """Devuelve los datos editables de un mantenimiento (para el modal de edición)."""
    from .models import Mantenimiento

    try:
        m = Mantenimiento.objects.select_related('chromebook').get(id=id)
    except Mantenimiento.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Mantenimiento no encontrado.'})

    return JsonResponse({'success': True, 'data': {
        'id': m.id,
        'chromebook': f'{m.chromebook.codigo} - {m.chromebook.marca} {m.chromebook.modelo}',
        'tipo': m.tipo,
        'descripcion_problema': m.descripcion_problema or '',
        'tecnico': m.tecnico or '',
        'costo': str(m.costo),
        'en_garantia': m.en_garantia,
        'fecha_inicio': m.fecha_inicio.strftime('%Y-%m-%d') if m.fecha_inicio else '',
    }})


@csrf_exempt
def api_editar_mantenimiento(request, id):
    """Edita los datos de un mantenimiento. No toca el estado (eso lo hace 'Finalizar')."""
    from .models import Mantenimiento

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})

    try:
        m = Mantenimiento.objects.get(id=id)
    except Mantenimiento.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Mantenimiento no encontrado.'})

    data = json.loads(request.body)
    m.tipo = data.get('tipo', m.tipo)
    m.descripcion_problema = data.get('descripcion_problema', m.descripcion_problema)
    m.tecnico = data.get('tecnico', m.tecnico)
    m.costo = data.get('costo', m.costo) or 0
    m.en_garantia = bool(data.get('en_garantia', m.en_garantia))
    fecha_inicio = data.get('fecha_inicio')
    if fecha_inicio:
        m.fecha_inicio = fecha_inicio
    m.save()

    return JsonResponse({'success': True, 'message': 'Mantenimiento actualizado.'})


@login_required
def finalizar_mantenimiento(request, id):
    """Finalizar un mantenimiento"""
    from .models import Mantenimiento
    from django.contrib import messages
    from django.utils import timezone
    
    try:
        mantenimiento = Mantenimiento.objects.get(id=id)
        
        if request.method == 'POST':
            mantenimiento.descripcion_solucion = request.POST.get('descripcion_solucion', '')
            mantenimiento.fecha_fin = timezone.now().date()
            mantenimiento.estado = 'finalizado'
            mantenimiento.save()
            
            # Devolver Chromebook a disponible y su condición a 'bueno'
            # (ya fue revisado/reparado).
            chromebook = mantenimiento.chromebook
            chromebook.estado = 'disponible'
            chromebook.condicion = 'bueno'
            chromebook.save()
            
            messages.success(request, f'Mantenimiento finalizado. {chromebook.codigo} disponible.')
            return redirect('prestamos:lista_mantenimientos')
        
        contexto = {
            'titulo_pagina': 'Finalizar Mantenimiento - CRAI UNEMI',
            'mantenimiento': mantenimiento,
        }
        return render(request, 'prestamos/mantenimiento/finalizar.html', contexto)
        
    except Mantenimiento.DoesNotExist:
        messages.error(request, 'Mantenimiento no encontrado.')
        return redirect('prestamos:lista_mantenimientos')












@login_required
def registro_rapido(request):
    _activar_reservas_pendientes()
    ahora = timezone.localtime()
    hoy = ahora.date()
    # El contador principal refleja la disponibilidad real "ahora" (igual que el inventario
    # y el dashboard): una reserva pendiente, sea de hoy o de otro día, ya descuenta.
    disponibles = _disponibles_inventario()
    disponibles_manana = _disponibles_efectivos(hoy + timedelta(days=1))
    prestamos_hoy = Prestamo.objects.filter(fecha_prestamo__date=hoy).select_related('estudiante', 'chromebook').order_by('-fecha_prestamo')
    total_hoy = prestamos_hoy.count()

    return render(request, 'prestamos/registro_rapido/registro_rapido.html', {
        'titulo_pagina': 'Nuevo Préstamo - CRAI UNEMI',
        'disponibles': disponibles, 'disponibles_manana': disponibles_manana,
        'prestamos_hoy': prestamos_hoy, 'total_hoy': total_hoy,
        'fecha_hoy': hoy.strftime('%Y-%m-%d'),
        'fecha_manana': (hoy + timedelta(days=1)).strftime('%Y-%m-%d'),
        'hora_actual': ahora.strftime('%H:%M'),
        'hora_mas_dos': (ahora + timedelta(hours=2)).strftime('%H:%M'),
    })


@login_required
def lista_estudiantes(request):
    from .models import Reserva, Carrera

    # Marca como 'vencida' las reservas pendientes cuyo retiro ya caducó, para que el
    # conteo y la lista de vencidos del admin reflejen el estado real.
    _expirar_reservas_vencidas()

    estudiantes_con_prestamos = Prestamo.objects.values_list('estudiante_id', flat=True).distinct()
    estudiantes_con_reservas = Reserva.objects.values_list('estudiante__usuario__user_id', flat=True).distinct()
    usuarios_activos_ids = set(list(estudiantes_con_prestamos) + list(estudiantes_con_reservas))

    estudiantes = Estudiante.objects.select_related('usuario__user', 'carrera').filter(
        usuario__user__id__in=usuarios_activos_ids
    ).order_by('-usuario__user__date_joined')

    prestamos_activos_ids = list(Prestamo.objects.filter(estado='activo').values_list('estudiante_id', flat=True).distinct())

    # Los vencidos del admin incluyen tanto préstamos vencidos como reservas que caducaron
    # sin retirarse (una reserva vencida nunca llega a generar un Préstamo).
    reservas_vencidas_lista = Reserva.objects.filter(estado='vencida').select_related(
        'estudiante__usuario__user', 'carrera'
    ).order_by('-fecha_uso', '-hora_inicio')[:10]
    vencidos = Prestamo.objects.filter(estado='vencido').count() + Reserva.objects.filter(estado='vencida').count()

    prestamos_activos_lista = Prestamo.objects.filter(estado='activo').select_related('estudiante', 'chromebook').order_by('fecha_devolucion')[:10]
    prestamos_vencidos_lista = Prestamo.objects.filter(estado='vencido').select_related('estudiante', 'chromebook').order_by('-fecha_devolucion')[:10]

    contexto = {
        'titulo_pagina': 'Estudiantes - CRAI UNEMI',
        'estudiantes': estudiantes,
        'total_estudiantes': estudiantes.count(),
        'estudiantes_activos': estudiantes.filter(usuario__user__id__in=prestamos_activos_ids).count(),
        'vencidos': vencidos,
        'prestamos_activos_ids': prestamos_activos_ids,
        'prestamos_activos_lista': prestamos_activos_lista,
        'prestamos_vencidos_lista': prestamos_vencidos_lista,
        'reservas_vencidas_lista': reservas_vencidas_lista,
        # Conteo mostrado en el panel de monitoreo (préstamos + reservas vencidas listadas).
        'monitoreo_vencidos_count': len(prestamos_vencidos_lista) + len(reservas_vencidas_lista),
        'carreras': Carrera.objects.all(),
    }
    return render(request, 'prestamos/estudiantes/lista.html', contexto)


@csrf_exempt
def api_perfil_estudiante(request, id):
    from .models import Evidencia, Reserva
    from datetime import datetime

    # Las reservas vencidas deben quedar reflejadas también aquí.
    _expirar_reservas_vencidas()

    try:
        estudiante = Estudiante.objects.select_related('usuario__user', 'carrera').get(id=id)
        user = estudiante.usuario.user

        prestamos = Prestamo.objects.filter(estudiante=user).select_related('chromebook').order_by('-fecha_prestamo')[:15]

        # Evidencias por préstamo (preferimos la de devolución; si no, la de entrega).
        prestamo_ids = [p.id for p in prestamos]
        fotos_por_prestamo = {}
        if prestamo_ids:
            for ev in Evidencia.objects.filter(prestamo_id__in=prestamo_ids).order_by('fecha_subida'):
                if not ev.foto:
                    continue
                actual = fotos_por_prestamo.get(ev.prestamo_id)
                # 'devolucion' tiene prioridad sobre cualquier otra evidencia previa.
                if actual is None or ev.tipo == 'devolucion':
                    fotos_por_prestamo[ev.prestamo_id] = {'url': ev.foto.url, 'tipo': ev.tipo}

        # Reservas que NO se convirtieron en préstamo (vencidas, canceladas, pendientes...).
        # Si una reserva se confirmó y generó un Préstamo, ya aparece en la sección de préstamos.
        reservas = Reserva.objects.filter(estudiante=estudiante).exclude(
            prestamos__isnull=False
        ).order_by('-fecha_uso', '-hora_inicio')[:15]

        # Cada entrada lleva una clave de orden (datetime) para mezclar préstamos y reservas.
        entradas = []
        total = 0
        activos = 0
        vencidos = 0

        for p in prestamos:
            total += 1
            if p.estado == 'activo':
                activos += 1
            elif p.estado == 'vencido':
                vencidos += 1
            foto = fotos_por_prestamo.get(p.id)
            entradas.append((p.fecha_prestamo, {
                'tipo': 'prestamo',
                'codigo': p.chromebook.codigo,
                'fecha': p.fecha_prestamo.strftime('%d/%m/%Y %H:%M') if p.fecha_prestamo else '-',
                'fecha_devuelto': p.fecha_devuelto.strftime('%d/%m/%Y %H:%M') if p.fecha_devuelto else None,
                'duracion': p.duracion_horas,
                'estado': p.estado,
                'foto_url': foto['url'] if foto else None,
                'foto_tipo': foto['tipo'] if foto else None,
            }))

        for r in reservas:
            total += 1
            if r.estado == 'vencida':
                vencidos += 1
            clave = timezone.make_aware(datetime.combine(r.fecha_uso, r.hora_inicio))
            entradas.append((clave, {
                'tipo': 'reserva',
                'codigo': 'Reserva',
                'fecha': clave.strftime('%d/%m/%Y %H:%M'),
                'fecha_devuelto': None,
                'duracion': r.calcular_duracion(),
                'estado': r.estado,
                'foto_url': None,
                'foto_tipo': None,
            }))

        entradas.sort(key=lambda e: e[0], reverse=True)
        historial = [e[1] for e in entradas]

        return JsonResponse({
            'avatar': f'{user.first_name[0].upper()}{user.last_name[0].upper()}',
            'foto_url': estudiante.usuario.foto.url if estudiante.usuario.foto else None,
            'nombre': user.get_full_name() or user.username,
            'cedula': estudiante.usuario.cedula,
            'carrera': estudiante.carrera.nombre,
            'semestre': estudiante.semestre,
            'email': user.email or '-',
            'resumen': {'total': total, 'activos': activos, 'vencidos': vencidos},
            'historial': historial,
        })
    except Estudiante.DoesNotExist:
        return JsonResponse({'error': 'Estudiante no encontrado'}, status=404)


@csrf_exempt
def verificar_codigo_reservacion(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        codigo = data.get('codigo', '').strip().upper()
        
        try:
            from .models import Reserva
            reserva = Reserva.objects.select_related('estudiante__usuario__user', 'estudiante__carrera').get(codigo_verificacion=codigo)

            # Aviso anticipado: ¿se puede activar ahora? (mismo criterio que el bloqueo
            # duro de confirmar_prestamo). Permite deshabilitar el botón antes de la foto.
            puede_activar, ventana_msg = _validar_ventana_reserva(reserva)

            return JsonResponse({'success': True, 'data': {
                'nombre': reserva.estudiante.usuario.user.get_full_name(),
                'cedula': reserva.estudiante.usuario.cedula,
                'carrera': reserva.estudiante.carrera.nombre,
                'semestre': reserva.estudiante.semestre,
                'fecha_uso': reserva.fecha_uso.strftime('%d/%m/%Y'),
                'horario': f'{reserva.hora_inicio.strftime("%H:%M")} - {reserva.hora_fin.strftime("%H:%M")}',
                'duracion': f'{reserva.calcular_duracion()} horas',
                'estado': reserva.estado,
                'reserva_id': reserva.id,
                'puede_activar': puede_activar,
                'ventana_msg': ventana_msg,
            }})
        except Reserva.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Código no encontrado.'})
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


@csrf_exempt
def revelar_codigo_reserva(request):
    """Revela el código de una reserva pendiente SOLO si la cédula coincide.

    Para el caso en que el estudiante olvidó su código: el recepcionista ingresa
    la cédula y, si corresponde al dueño de la reserva, se muestra el código.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})

    from .models import Reserva
    data = json.loads(request.body)
    reserva_id = data.get('reserva_id')
    cedula = (data.get('cedula') or '').strip()

    if not cedula:
        return JsonResponse({'success': False, 'message': 'Ingresa la cédula del estudiante.'})

    try:
        reserva = Reserva.objects.select_related('estudiante__usuario').get(id=reserva_id, estado='pendiente')
    except Reserva.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Reserva no encontrada o ya procesada.'})

    if reserva.estudiante.usuario.cedula != cedula:
        return JsonResponse({'success': False, 'message': 'La cédula no coincide con el estudiante de esta reserva.'})

    return JsonResponse({'success': True, 'codigo': reserva.codigo_verificacion})


def _validar_ventana_reserva(reserva):
    """Valida que la reserva pueda ACTIVARSE ahora (estado, fecha y horario).

    Solo una reserva 'pendiente' se activa, y únicamente el día de su uso dentro de
    su horario (con 10 min de gracia antes del inicio). Evita que un código válido
    para otro día/hora —o una reserva ya vencida/procesada— active el préstamo.
    Devuelve (ok: bool, mensaje: str).
    """
    # 1) Estado: solo las pendientes son activables.
    if reserva.estado != 'pendiente':
        motivos = {
            'confirmada': 'Esta reservación ya fue confirmada; el equipo ya se entregó.',
            'completada': 'Esta reservación ya se completó.',
            'cancelada': 'Esta reservación fue cancelada.',
            'vencida': 'Esta reservación venció y ya no está vigente. El estudiante debe generar una nueva.',
        }
        return False, motivos.get(reserva.estado, 'Esta reservación ya fue procesada.')

    ahora = timezone.localtime()
    hoy = ahora.date()
    h_ini = reserva.hora_inicio.strftime('%H:%M')
    h_fin = reserva.hora_fin.strftime('%H:%M')

    # 2) Fecha: para otro día.
    if reserva.fecha_uso > hoy:
        return False, (f'Todavía no es el momento: esta reserva es para el '
                       f'{reserva.fecha_uso.strftime("%d/%m/%Y")} ({h_ini}–{h_fin}). '
                       f'Podrás activarla ese día, dentro de su horario.')
    if reserva.fecha_uso < hoy:
        return False, (f'Esta reserva era para el {reserva.fecha_uso.strftime("%d/%m/%Y")} '
                       f'y ya no está vigente. El estudiante debe generar una nueva.')

    # 3) Horario del día de hoy.
    ahora_naive = ahora.replace(tzinfo=None)
    inicio = datetime.combine(hoy, reserva.hora_inicio) - timedelta(minutes=10)
    fin = datetime.combine(hoy, reserva.hora_fin)
    if ahora_naive < inicio:
        return False, (f'Todavía no es el momento. El horario de esta reserva es '
                       f'{h_ini}–{h_fin}; podrás activarla a partir de las {h_ini}.')
    if ahora_naive > fin:
        return False, (f'El horario de esta reserva ({h_ini}–{h_fin}) ya pasó, por lo que '
                       f'venció. El estudiante debe generar una nueva reservación.')
    return True, ''


@csrf_exempt
def confirmar_prestamo(request):
    """API para confirmar un préstamo desde el código de reservación"""
    if request.method == 'POST':
        data = json.loads(request.body)
        reserva_id = data.get('reserva_id')
        foto_nombre = data.get('foto_nombre', '')

        try:
            from .models import Reserva, Evidencia
            from django.core.files import File

            reserva = Reserva.objects.get(id=reserva_id)

            # El CRAI solo entrega equipos en su horario de atención (08:00–17:00).
            if not _crai_abierto():
                return JsonResponse({'success': False, 'message': (
                    f'El CRAI atiende de {CRAI_HORA_APERTURA.strftime("%H:%M")} a '
                    f'{CRAI_HORA_CIERRE.strftime("%H:%M")}. No es posible activar préstamos fuera de ese horario.'
                )})

            # Bloqueo único: estado (solo pendientes), fecha y horario de la reserva.
            ventana_ok, ventana_msg = _validar_ventana_reserva(reserva)
            if not ventana_ok:
                return JsonResponse({'success': False, 'message': ventana_msg})

            chromebook = Chromebook.objects.filter(estado='disponible').first()
            
            if not chromebook:
                return JsonResponse({'success': False, 'message': 'No hay Chromebooks disponibles.'})
            
            ahora = timezone.now()
            duracion_td = reserva.duracion_timedelta()
            prestamo = Prestamo.objects.create(
                estudiante=reserva.estudiante.usuario.user,
                chromebook=chromebook,
                reserva=reserva,
                fecha_prestamo=ahora,
                fecha_devolucion=ahora + duracion_td,
                duracion_horas=max(1, round(duracion_td.total_seconds() / 3600)),
                codigo_verificacion=reserva.codigo_verificacion,
                estado='activo'
            )
            
            chromebook.estado = 'prestado'
            chromebook.save()
            reserva.estado = 'confirmada'
            reserva.save()
            
            # Guardar evidencia
            if foto_nombre:
                temp_path = os.path.join(settings.MEDIA_ROOT, 'evidencias', foto_nombre)
                if os.path.exists(temp_path):
                    evidencia = Evidencia.objects.create(prestamo=prestamo, tipo='entrega', descripcion='Evidencia de entrega')
                    with open(temp_path, 'rb') as f:
                        evidencia.foto.save(foto_nombre, File(f), save=True)
                    print(f'✅ Evidencia guardada para préstamo #{prestamo.id}')
            
            return JsonResponse({'success': True, 'message': f'Préstamo confirmado. {chromebook.codigo} asignado.'})
            
        except Reserva.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Reserva no encontrada.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


@csrf_exempt
def api_buscar_chromebook(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        codigo = data.get('codigo', '').strip()
        
        try:
            if '-' in codigo:
                chromebook = Chromebook.objects.get(codigo=codigo)
            else:
                chromebook = Chromebook.objects.get(codigo=f'CB-{codigo.zfill(3)}')
        except Chromebook.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Chromebook no encontrado.'})

        # Estado efectivo: una reserva pendiente aparta un cupo aunque sea para otro día.
        # Usamos la misma lógica que el inventario para que aquí también salga "pendiente
        # a reserva" en vez de "disponible".
        chromebooks = list(Chromebook.objects.all().order_by('codigo'))
        _marcar_pendiente_reserva(chromebooks)
        estado_efectivo = next(
            (cb.estado_efectivo for cb in chromebooks if cb.id == chromebook.id),
            chromebook.estado,
        )

        return JsonResponse({'success': True, 'data': {
            'id': chromebook.id, 'codigo': chromebook.codigo,
            'marca': chromebook.marca, 'modelo': chromebook.modelo,
            'estado': estado_efectivo, 'condicion': chromebook.condicion,
        }})


@csrf_exempt
def api_buscar_estudiante(request):
    if request.method == 'POST':
        from .services.api_estudiantes import obtener_estudiante, ApiEstudiantesError
        from .services.sincronizacion import sincronizar_estudiante

        data = json.loads(request.body)
        cedula = data.get('cedula', '').strip()

        estudiante = (
            Estudiante.objects
            .select_related('usuario__user', 'carrera')
            .filter(usuario__cedula=cedula)
            .first()
        )

        # Sync on-demand: si no está en el espejo local, traerlo de matrículas.
        if estudiante is None:
            from .models import ConfiguracionSistema
            if not ConfiguracionSistema.obtener().api_matriculas_activa:
                return JsonResponse({'success': False, 'message': 'Estudiante no encontrado localmente y la API de matrículas está desconectada.'})
            try:
                data_api = obtener_estudiante(cedula)
            except ApiEstudiantesError:
                return JsonResponse({'success': False, 'message': 'Servicio de matrículas no disponible. Intenta más tarde.'})
            if data_api:
                estudiante, _ = sincronizar_estudiante(data_api)

        if estudiante is None:
            return JsonResponse({'success': False, 'message': 'Estudiante no encontrado.'})

        # Reservaciones vigentes del estudiante: si ya tiene alguna pendiente/confirmada
        # se avisa en recepción (mismo criterio de "vigentes" que el resto del sistema).
        from .models import Reserva
        _expirar_reservas_vencidas()
        reservas_vigentes = Reserva.objects.filter(
            estudiante=estudiante, estado__in=['pendiente', 'confirmada'],
        ).order_by('fecha_uso', 'hora_inicio')
        reservas_info = [{
            'codigo': r.codigo_verificacion,
            'fecha': r.fecha_uso.strftime('%d/%m/%Y'),
            'hora': r.hora_inicio.strftime('%H:%M') if r.hora_inicio else '',
            'estado': r.estado,
        } for r in reservas_vigentes]

        perfil = estudiante.usuario
        return JsonResponse({'success': True, 'data': {
            'id': estudiante.id, 'user_id': perfil.user.id,
            'nombre': perfil.user.get_full_name() or perfil.user.username,
            'cedula': perfil.cedula,
            'carrera': estudiante.carrera.nombre if estudiante.carrera else 'No registrada',
            'semestre': estudiante.semestre,
            'reservas_pendientes': reservas_info,
        }})


def _expirar_reservas_vencidas():
    """Marca como 'vencida' las reservas 'pendiente' cuyo retiro no se hizo.

    Una reserva vence si pasaron 15 minutos de su hora de inicio (en su fecha de
    uso) y el estudiante no la confirmó en el CRAI. La reserva no aparta un equipo
    concreto, así que solo cambia de estado (sale del conteo de vigentes).
    """
    from datetime import datetime, timedelta
    from .models import Reserva

    ahora = timezone.now()
    pendientes = Reserva.objects.filter(estado='pendiente')
    vencidas_ids = []
    for r in pendientes:
        limite = timezone.make_aware(
            datetime.combine(r.fecha_uso, r.hora_inicio)
        ) + timedelta(minutes=15)
        if ahora > limite:
            vencidas_ids.append(r.id)
    if vencidas_ids:
        Reserva.objects.filter(id__in=vencidas_ids).update(estado='vencida')


def _reservas_por_vencer():
    """Reservas 'pendiente' próximas a su hora (a 15 minutos o menos de vencer).

    La cuenta empieza 15 minutos ANTES de la hora de inicio de la reserva y se
    mantiene durante los 15 minutos de gracia posteriores (hasta que la reserva
    expira y pasa a 'vencida'). Así una reserva a la que le faltan, por ejemplo,
    14 minutos para su hora ya aparece como "por vencer".
    """
    from datetime import datetime, timedelta
    from .models import Reserva

    ahora = timezone.now()
    cuenta = 0
    for r in Reserva.objects.filter(estado='pendiente'):
        inicio = timezone.make_aware(datetime.combine(r.fecha_uso, r.hora_inicio))
        if inicio - timedelta(minutes=15) <= ahora < inicio + timedelta(minutes=15):
            cuenta += 1
    return cuenta


def _disponibles_efectivos(fecha=None):
    """Chromebooks realmente disponibles para una fecha, según las reservas pendientes de ESE día.

    Una reserva no aparta un equipo concreto, pero sí 'consume' un cupo del día: al
    contador de equipos libres le restamos las reservas pendientes con esa fecha de uso,
    para no ofrecer más equipos de los que quedan tras honrar las reservas. Sin fecha,
    usa hoy.
    """
    from .models import Chromebook, Reserva
    if fecha is None:
        fecha = timezone.localdate()
    fisicos = Chromebook.objects.filter(estado='disponible').count()
    reservas = Reserva.objects.filter(
        estado='pendiente', fecha_uso=fecha
    ).count()
    return max(0, fisicos - reservas)


def _disponibles_inventario():
    """Chromebooks disponibles 'ahora mismo', descontando TODAS las reservas pendientes.

    Es la misma cuenta que muestra el inventario (`_marcar_pendiente_reserva`): una reserva
    pendiente aparta un cupo aunque sea para otro día. Sirve para que el dashboard y la
    búsqueda de préstamo reflejen lo mismo que el inventario, en lugar de mirar solo las
    reservas de hoy.
    """
    from .models import Chromebook, Reserva
    _expirar_reservas_vencidas()
    fisicos = Chromebook.objects.filter(estado='disponible').count()
    pendientes = Reserva.objects.filter(estado='pendiente').count()
    return max(0, fisicos - pendientes)


def _activar_reservas_pendientes():
    """Convierte en 'activo' las reservas cuya hora de inicio ya llegó."""
    ahora = timezone.now()
    pendientes = Prestamo.objects.filter(
        estado='reservado', fecha_prestamo__lte=ahora, fecha_devolucion__gt=ahora
    ).select_related('chromebook')
    for p in pendientes:
        p.estado = 'activo'
        p.save(update_fields=['estado'])
        if p.chromebook.estado in ('disponible', 'reservado'):
            p.chromebook.estado = 'prestado'
            p.chromebook.save(update_fields=['estado'])


@csrf_exempt
def api_registrar_prestamo(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'})

    from datetime import datetime, timedelta
    data = json.loads(request.body)
    chromebook_id = data.get('chromebook_id')
    user_id = data.get('user_id')
    fecha = data.get('fecha')               # 'YYYY-MM-DD'
    hora_inicio = data.get('hora_inicio')   # 'HH:MM'
    hora_fin = data.get('hora_fin')         # 'HH:MM'

    if not (fecha and hora_inicio and hora_fin):
        return JsonResponse({'success': False, 'message': 'Indica fecha, hora de inicio y hora de fin.'})

    try:
        inicio = timezone.make_aware(datetime.strptime(f'{fecha} {hora_inicio}', '%Y-%m-%d %H:%M'))
        fin = timezone.make_aware(datetime.strptime(f'{fecha} {hora_fin}', '%Y-%m-%d %H:%M'))
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Fecha u hora con formato inválido.'})

    if fin <= inicio:
        return JsonResponse({'success': False, 'message': 'La hora de fin debe ser posterior a la de inicio.'})

    ahora = timezone.now()
    if fin <= ahora:
        return JsonResponse({'success': False, 'message': 'El horario indicado ya pasó.'})

    # El turno del préstamo/reserva debe caer dentro del horario CRAI (08:00–17:00).
    if inicio.time() < CRAI_HORA_APERTURA or fin.time() > CRAI_HORA_CIERRE:
        return JsonResponse({'success': False, 'message': (
            f'El horario de atención del CRAI es de {CRAI_HORA_APERTURA.strftime("%H:%M")} a '
            f'{CRAI_HORA_CIERRE.strftime("%H:%M")}. Ajusta la hora del préstamo.'
        )})

    import random, string
    from .models import Reserva, Estudiante

    try:
        estudiante_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Usuario no encontrado.'})

    # Gracia de 2 min: si el inicio cae dentro de los próximos/últimos 2 minutos se
    # trata como préstamo INMEDIATO. Evita el bug de que al pasar un minuto la hora
    # quedaba "en el pasado" y el préstamo no se registraba (se confundía con reserva).
    es_reserva = inicio > ahora + timedelta(minutes=2)

    # ── RESERVA (para más tarde o para mañana): genera una Reserva pendiente con
    #    código. Aparece en "Reservaciones Pendientes" y el estudiante usa el código.
    if es_reserva:
        try:
            estudiante = Estudiante.objects.select_related('carrera').get(usuario__user_id=user_id)
        except Estudiante.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Ese usuario no es un estudiante; no se puede generar la reserva.'})

        # Límite de reservas vigentes por estudiante (mismo criterio que el portal del estudiante).
        vigentes = Reserva.objects.filter(
            estudiante=estudiante,
            estado__in=['pendiente', 'confirmada'],
        ).count()
        if vigentes >= MAX_RESERVAS_VIGENTES:
            return JsonResponse({
                'success': False,
                'message': f'El estudiante ya tiene {MAX_RESERVAS_VIGENTES} reservas activas. '
                           'Debe completar o cancelar alguna antes de reservar otra.',
            })

        # Cupo del día: no permitir más reservas que Chromebooks disponibles para esa fecha.
        if _disponibles_efectivos(inicio.date()) <= 0:
            return JsonResponse({
                'success': False,
                'message': 'No quedan Chromebooks disponibles para esa fecha. Elige otro día.',
            })

        while True:
            codigo = ''.join(random.choices(string.digits, k=6))
            if not Reserva.objects.filter(codigo_verificacion=codigo).exists():
                break

        Reserva.objects.create(
            estudiante=estudiante, carrera=estudiante.carrera,
            fecha_uso=inicio.date(), hora_inicio=inicio.time(), hora_fin=fin.time(),
            estado='pendiente', codigo_verificacion=codigo,
            motivo='Reserva registrada en recepción',
        )
        return JsonResponse({
            'success': True,
            'codigo': codigo,
            'es_reserva': True,
            'message': f'Reserva creada para el {fecha} de {hora_inicio} a {hora_fin}. '
                       f'Código para el estudiante: {codigo}.',
        })

    # ── PRÉSTAMO INMEDIATO: asigna el equipo ahora.
    try:
        chromebook = Chromebook.objects.get(id=chromebook_id)
    except Chromebook.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Chromebook no encontrado.'})

    if chromebook.estado == 'mantenimiento':
        return JsonResponse({'success': False, 'message': 'Este Chromebook está en mantenimiento.'})

    # Validar solape con otros préstamos/reservas del mismo equipo.
    solapado = Prestamo.objects.filter(
        chromebook=chromebook,
        estado__in=['reservado', 'activo', 'vencido'],
        fecha_prestamo__lt=fin,
        fecha_devolucion__gt=inicio,
    ).exists()
    if solapado:
        return JsonResponse({'success': False, 'message': 'El Chromebook ya tiene un préstamo o reserva en ese horario.'})

    codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    duracion = max(1, round((fin - inicio).total_seconds() / 3600))

    prestamo = Prestamo.objects.create(
        estudiante=estudiante_user, chromebook=chromebook,
        fecha_prestamo=inicio, fecha_devolucion=fin,
        estado='activo', duracion_horas=duracion, codigo_verificacion=codigo,
    )
    chromebook.estado = 'prestado'
    chromebook.save(update_fields=['estado'])

    # Guardar foto de evidencia si la recepción la capturó (opcional).
    foto_nombre = data.get('foto_nombre', '')
    if foto_nombre:
        # Evita rutas fuera de la carpeta de evidencias.
        foto_nombre = os.path.basename(foto_nombre)
        from .models import Evidencia
        from django.core.files import File
        temp_path = os.path.join(settings.MEDIA_ROOT, 'evidencias', foto_nombre)
        if os.path.exists(temp_path):
            # Nombre definitivo con la convención de entrega.
            nombre_completo = (estudiante_user.get_full_name() or estudiante_user.username).replace(' ', '_')
            nombre_limpio = unicodedata.normalize('NFKD', nombre_completo).encode('ASCII', 'ignore').decode('ASCII')
            nombre_final = f'{nombre_limpio}_ENT_{chromebook.codigo}_{prestamo.id}.jpg'
            evidencia = Evidencia.objects.create(prestamo=prestamo, tipo='entrega', descripcion='Evidencia de entrega')
            with open(temp_path, 'rb') as f:
                evidencia.foto.save(nombre_final, File(f), save=True)
            # Limpia la foto temporal previa al registro.
            if foto_nombre.startswith('temp_entrega_'):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    return JsonResponse({
        'success': True,
        'es_reserva': False,
        'message': f'Préstamo registrado. {chromebook.codigo} asignado.',
    })
        




@login_required
def ficha_estudiantil(request):
    """Buscador de fichas estudiantiles"""
    estudiante_encontrado = None
    error = None
    
    if request.method == 'POST':
        busqueda = request.POST.get('busqueda', '').strip()
        
        if busqueda:
            from .models import Estudiante, Usuario as PerfilUsuario
            from django.db.models import Q
            
            # Buscar por cédula, nombre o username
            estudiantes = Estudiante.objects.select_related(
                'usuario__user', 'carrera', 'carrera__facultad'
            ).filter(
                Q(usuario__cedula__icontains=busqueda) |
                Q(usuario__user__first_name__icontains=busqueda) |
                Q(usuario__user__last_name__icontains=busqueda) |
                Q(usuario__user__username__icontains=busqueda)
            )
            
            if estudiantes.exists():
                estudiante_encontrado = estudiantes.first()
            elif busqueda.isdigit() and len(busqueda) == 10:
                # Sync on-demand por cédula desde matrículas y re-búsqueda.
                from .services.api_estudiantes import obtener_estudiante, ApiEstudiantesError
                from .services.sincronizacion import sincronizar_estudiante
                try:
                    data_api = obtener_estudiante(busqueda)
                except ApiEstudiantesError:
                    data_api = None
                    error = 'Servicio de matrículas no disponible. Intenta más tarde.'
                if data_api:
                    nuevo, _ = sincronizar_estudiante(data_api)
                    estudiante_encontrado = Estudiante.objects.select_related(
                        'usuario__user', 'carrera', 'carrera__facultad'
                    ).get(pk=nuevo.pk)
                elif not error:
                    error = 'No se encontró ningún estudiante con esos datos.'
            else:
                error = 'No se encontró ningún estudiante con esos datos.'
    
    contexto = {
        'titulo_pagina': 'Ficha Estudiantil - CRAI UNEMI',
        'estudiante': estudiante_encontrado,
        'error': error,
    }
    return render(request, 'prestamos/estudiantes/ficha_estudiantil.html', contexto)




@login_required
def ajustes(request):
    """Página de configuración del sistema"""
    from .models import SesionUsuario, ConfiguracionSistema

    sesiones = SesionUsuario.objects.filter(
        usuario=request.user
    ).order_by('-fecha_inicio')[:10]

    contexto = {
        'titulo_pagina': 'Ajustes - CRAI UNEMI',
        'sesiones': sesiones,
        'api_activa': ConfiguracionSistema.obtener().api_matriculas_activa,
    }
    return render(request, 'prestamos/ajustes/ajustes.html', contexto)


@login_required
def perfil(request):
    """Perfil del usuario: datos, foto y cambio de contraseña."""
    perfil_usuario = getattr(request.user, 'perfil', None)
    rol = request.user.groups.values_list('name', flat=True).first() or 'Usuario'
    return render(request, 'prestamos/perfil/perfil.html', {
        'titulo_pagina': 'Mi Perfil - CRAI UNEMI',
        'perfil_usuario': perfil_usuario,
        'rol': rol,
    })


@login_required
def actualizar_foto_perfil(request):
    """Sube/actualiza la foto de perfil del usuario."""
    from django.contrib import messages
    if request.method == 'POST' and request.FILES.get('foto'):
        perfil_usuario = getattr(request.user, 'perfil', None)
        if perfil_usuario is None:
            messages.error(request, 'No se encontró el perfil del usuario.')
        else:
            perfil_usuario.foto = request.FILES['foto']
            perfil_usuario.save(update_fields=['foto'])
            messages.success(request, 'Foto de perfil actualizada.')
    return redirect('prestamos:perfil')


@login_required
def api_actualizar_telefono(request):
    """Actualiza solo el celular del perfil (cédula y nombres no se tocan)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'})
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Solicitud inválida.'})

    telefono = re.sub(r'\D', '', str(data.get('telefono', '')))
    if telefono and len(telefono) != 10:
        return JsonResponse({'success': False, 'message': 'El celular debe tener 10 dígitos.'})

    perfil_usuario = getattr(request.user, 'perfil', None)
    if perfil_usuario is None:
        return JsonResponse({'success': False, 'message': 'No se encontró el perfil del usuario.'})
    perfil_usuario.telefono = telefono
    perfil_usuario.save(update_fields=['telefono'])
    return JsonResponse({'success': True, 'telefono': telefono or '—', 'message': 'Celular actualizado.'})


def _limpiar_pwd_session(request):
    for k in ('pwd_codigo', 'pwd_nueva', 'pwd_expira'):
        request.session.pop(k, None)


def _enmascarar_correo(correo):
    """Devuelve el correo parcialmente oculto, p.ej. an***@gmail.com."""
    try:
        usuario, dominio = correo.split('@', 1)
    except ValueError:
        return correo
    visible = usuario[:2] if len(usuario) > 2 else usuario[:1]
    return f'{visible}***@{dominio}'


@login_required
def api_solicitar_codigo_password(request):
    """Paso 1: valida la contraseña actual y la nueva, y envía un código al correo."""
    from django.core.mail import send_mail
    import random

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'})
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Solicitud inválida.'})

    actual = data.get('actual', '')
    nueva = data.get('nueva', '')
    confirmar = data.get('confirmar', '')

    if not request.user.check_password(actual):
        return JsonResponse({'success': False, 'message': 'La contraseña actual no es correcta.'})
    if len(nueva) < 8:
        return JsonResponse({'success': False, 'message': 'La nueva contraseña debe tener al menos 8 caracteres.'})
    if nueva != confirmar:
        return JsonResponse({'success': False, 'message': 'La confirmación no coincide con la nueva contraseña.'})
    if not request.user.email:
        return JsonResponse({'success': False, 'message': 'No tienes un correo registrado para verificar el cambio.'})

    codigo = ''.join(random.choices('0123456789', k=6))
    request.session['pwd_codigo'] = codigo
    request.session['pwd_nueva'] = nueva
    request.session['pwd_expira'] = (timezone.now() + timedelta(minutes=10)).isoformat()

    try:
        send_mail(
            'Código de verificación - CRAI UNEMI',
            f'Tu código para cambiar la contraseña es: {codigo}\n\n'
            'Este código expira en 10 minutos. Si no solicitaste el cambio, ignora este correo.',
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False,
        )
    except Exception:
        _limpiar_pwd_session(request)
        return JsonResponse({'success': False, 'message': 'No se pudo enviar el correo. Intenta más tarde.'})

    return JsonResponse({
        'success': True,
        'correo': _enmascarar_correo(request.user.email),
        'message': 'Código enviado a tu correo.',
    })


@login_required
def api_confirmar_codigo_password(request):
    """Paso 2: valida el código del correo y aplica la nueva contraseña."""
    from django.contrib.auth import update_session_auth_hash

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'})
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Solicitud inválida.'})

    codigo = str(data.get('codigo', '')).strip()
    guardado = request.session.get('pwd_codigo')
    nueva = request.session.get('pwd_nueva')
    expira = request.session.get('pwd_expira')

    if not (guardado and nueva and expira):
        return JsonResponse({'success': False, 'message': 'No hay una solicitud de cambio activa. Vuelve a empezar.'})
    if timezone.now() > datetime.fromisoformat(expira):
        _limpiar_pwd_session(request)
        return JsonResponse({'success': False, 'message': 'El código expiró. Solicita uno nuevo.'})
    if codigo != guardado:
        return JsonResponse({'success': False, 'message': 'El código no es correcto.'})

    request.user.set_password(nueva)
    request.user.save()
    update_session_auth_hash(request, request.user)  # mantener la sesión
    _limpiar_pwd_session(request)
    return JsonResponse({'success': True, 'message': 'Contraseña actualizada correctamente.'})


def _es_tics(user):
    """Solo TICs/administradores acceden a la gestión de personal."""
    return user.is_superuser or user.groups.filter(name__in=['Administrador', 'Tics']).exists()


ROLES_PERSONAL = ('Recepcionista', 'Administrador')


@login_required
def gestion_personal(request):
    """Panel de administración: alta de personal y asignación de roles.

    Acceso restringido a administradores/TICs (ver _es_tics). El recepcionista no
    puede entrar ni por enlace ni por URL directa: se le redirige al dashboard.
    """
    from django.contrib import messages
    from django.contrib.auth.models import Group
    from .models import TipoUsuario
    from apps.prestamos.services.usuarios import generar_username, generar_username_unico

    if not _es_tics(request.user):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('prestamos:dashboard')

    if request.method == 'POST':
        accion = request.POST.get('accion', 'crear')

        # ---- Cambiar el rol de un usuario ya existente ----
        if accion == 'cambiar_rol':
            objetivo = User.objects.filter(id=request.POST.get('user_id')).first()
            nuevo_rol = (request.POST.get('rol') or '').strip()

            if objetivo is None:
                messages.error(request, 'Usuario no encontrado.')
            elif nuevo_rol not in ROLES_PERSONAL:
                messages.error(request, 'Rol no válido.')
            elif objetivo == request.user:
                messages.error(request, 'No puedes cambiar tu propio rol.')
            elif objetivo.is_superuser:
                messages.error(request, 'No se puede cambiar el rol de un superusuario.')
            else:
                objetivo.groups.remove(*Group.objects.filter(name__in=ROLES_PERSONAL))
                grupo, _ = Group.objects.get_or_create(name=nuevo_rol)
                objetivo.groups.add(grupo)
                tipo, _ = TipoUsuario.objects.get_or_create(nombre=nuevo_rol)
                perfil = getattr(objetivo, 'perfil', None)
                if perfil:
                    perfil.tipo_usuario = tipo
                    perfil.save(update_fields=['tipo_usuario'])
                messages.success(request, f'Rol actualizado: {objetivo.get_full_name() or objetivo.username} ahora es {nuevo_rol}.')
            return redirect('prestamos:gestion_personal')

        # ---- Eliminar una cuenta de personal ----
        if accion == 'eliminar':
            objetivo = User.objects.filter(id=request.POST.get('user_id')).first()

            if objetivo is None:
                messages.error(request, 'Usuario no encontrado.')
            elif objetivo == request.user:
                messages.error(request, 'No puedes eliminar tu propia cuenta.')
            elif objetivo.is_superuser:
                messages.error(request, 'No se puede eliminar un superusuario.')
            elif not objetivo.groups.filter(name__in=ROLES_PERSONAL).exists():
                messages.error(request, 'Solo puedes eliminar cuentas de personal.')
            else:
                nombre = objetivo.get_full_name() or objetivo.username
                objetivo.delete()
                messages.success(request, f'Cuenta eliminada: {nombre}.')
            return redirect('prestamos:gestion_personal')

        # ---- Crear una cuenta de personal ----
        nombres = (request.POST.get('nombres') or '').strip()
        apellidos = (request.POST.get('apellidos') or '').strip()
        cedula = (request.POST.get('cedula') or '').strip()
        telefono = (request.POST.get('telefono') or '').strip()
        correo = (request.POST.get('correo') or '').strip()
        password = (request.POST.get('password') or '').strip()
        rol = (request.POST.get('rol') or 'Recepcionista').strip()

        if not nombres or not apellidos:
            messages.error(request, 'Nombres y apellidos son obligatorios.')
        elif rol not in ROLES_PERSONAL:
            messages.error(request, 'Rol no válido.')
        elif not (cedula.isdigit() and len(cedula) == 10):
            messages.error(request, 'La cédula debe tener 10 dígitos.')
        elif PerfilUsuario.objects.filter(cedula=cedula).exists():
            messages.error(request, f'Ya existe un usuario con la cédula {cedula}.')
        elif not password or len(password) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
        else:
            username = generar_username_unico(nombres, apellidos)
            if not correo:
                correo = f'{generar_username(nombres, apellidos)}@unemi.edu.ec'

            grupo, _ = Group.objects.get_or_create(name=rol)
            tipo, _ = TipoUsuario.objects.get_or_create(nombre=rol)

            user = User.objects.create(
                username=username,
                first_name=nombres,
                last_name=apellidos,
                email=correo,
                is_active=True,
            )
            user.set_password(password)
            user.save()
            user.groups.add(grupo)

            PerfilUsuario.objects.create(
                user=user,
                tipo_usuario=tipo,
                cedula=cedula,
                telefono=telefono[:10],
                origen='local',
            )

            messages.success(request, f'{rol} creado. Usuario: {username} · Correo: {correo}')
            return redirect('prestamos:gestion_personal')

    # Listado del personal (recepcionistas y administradores registrados)
    personal = list(
        User.objects.filter(groups__name__in=ROLES_PERSONAL)
        .select_related('perfil')
        .prefetch_related('groups')
        .order_by('last_name', 'first_name')
        .distinct()
    )
    # Anota el rol principal y si es editable (no superusuario ni uno mismo)
    for p in personal:
        nombres_grupos = {g.name for g in p.groups.all()}
        p.rol_actual = 'Administrador' if 'Administrador' in nombres_grupos else 'Recepcionista'
        p.editable = (not p.is_superuser) and (p.id != request.user.id)

    contexto = {
        'titulo_pagina': 'Gestión de Personal - CRAI UNEMI',
        'personal': personal,
        'total_personal': len(personal),
        'total_admins': sum(1 for p in personal if p.rol_actual == 'Administrador'),
        'total_recep': sum(1 for p in personal if p.rol_actual == 'Recepcionista'),
    }
    return render(request, 'prestamos/personal/personal.html', contexto)



@csrf_exempt
def api_detalle_chromebook(request, id):
    """API para obtener detalles de un Chromebook"""
    import os
    from django.conf import settings
    
    try:
        cb = Chromebook.objects.get(id=id)
        
        # Buscar foto en la carpeta por código
        foto_url = None
        extensiones = ['.jpg', '.jpeg', '.png', '.webp']
        for ext in extensiones:
            ruta_foto = os.path.join(settings.MEDIA_ROOT, 'chromebooks', f'{cb.codigo}{ext}')
            if os.path.exists(ruta_foto):
                foto_url = f'{settings.MEDIA_URL}chromebooks/{cb.codigo}{ext}'
                break
        
        # Si tiene foto en el modelo, usar esa
        if cb.foto:
            foto_url = cb.foto.url
        
        return JsonResponse({
            'success': True,
            'data': {
                'codigo': cb.codigo,
                'marca': cb.marca,
                'modelo': cb.modelo,
                'serie': cb.serie,
                'estado': cb.estado,
                'condicion': cb.condicion,
                'notas': cb.notas,
                'foto_url': foto_url,
            }
        })
    except Chromebook.DoesNotExist:
        return JsonResponse({'success': False})




@csrf_exempt
def api_editar_chromebook(request, id):
    """API para editar un Chromebook"""
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            from .models import Mantenimiento
            cb = Chromebook.objects.get(id=id)
            estado_anterior = cb.estado
            nuevo_estado = data.get('estado', cb.estado)
            cb.marca = data.get('marca', cb.marca)
            cb.modelo = data.get('modelo', cb.modelo)
            cb.serie = data.get('serie', cb.serie)
            cb.estado = nuevo_estado
            cb.condicion = data.get('condicion', cb.condicion)
            cb.notas = data.get('notas', cb.notas)
            cb.save()

            # Si el equipo sale de mantenimiento desde el inventario, cerrar el/los
            # mantenimientos abiertos para que no queden "en proceso" descuadrados.
            if estado_anterior == 'mantenimiento' and nuevo_estado != 'mantenimiento':
                Mantenimiento.objects.filter(chromebook=cb, estado='en_proceso').update(
                    estado='finalizado',
                    fecha_fin=timezone.now().date(),
                )

            return JsonResponse({'success': True})
        except Chromebook.DoesNotExist:
            return JsonResponse({'success': False})
        

@csrf_exempt
def api_generar_qr_foto_chromebook(request):
    """Genera QR para subir foto de Chromebook desde celular"""
    if request.method == 'POST':
        data = json.loads(request.body)
        codigo = data.get('codigo', '')
        
        import uuid
        token = str(uuid.uuid4())[:8]
        
        # Guardar token
        qr_tokens[token] = {
            'codigo': codigo,
            'expiracion': timezone.now() + timedelta(minutes=2),
            'recibida': False
        }
        
        host = request.get_host()
        url_foto = f'http://{host}/prestamos/subir-foto-chromebook/{token}/'
        
        return JsonResponse({'success': True, 'token': token, 'url': url_foto})
    

def subir_foto_chromebook(request, token):
    """Página móvil para subir foto del Chromebook"""
    if token not in qr_tokens:
        return render(request, 'prestamos/evidencia/expirada.html')
    
    data = qr_tokens[token]
    
    if data['expiracion'] < timezone.now():
        del qr_tokens[token]
        return render(request, 'prestamos/evidencia/expirada.html')
    
    if request.method == 'POST' and request.FILES.get('foto'):
        import os
        foto = request.FILES['foto']
        codigo = data['codigo']
        
        # Guardar en media/chromebooks/
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'chromebooks')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Obtener extensión
        ext = os.path.splitext(foto.name)[1] or '.jpg'
        nombre_archivo = f'{codigo}{ext}'
        ruta_completa = os.path.join(temp_dir, nombre_archivo)
        
        with open(ruta_completa, 'wb') as f:
            for chunk in foto.chunks():
                f.write(chunk)
        
        qr_tokens[token]['recibida'] = True
        print(f'✅ Foto guardada: {nombre_archivo}')
        
        response = render(request, 'prestamos/evidencia/exitosa.html')
        response['ngrok-skip-browser-warning'] = 'true'
        return response
    
    response = render(request, 'prestamos/evidencia/subir.html', {'token': token})
    response['ngrok-skip-browser-warning'] = 'true'
    return response