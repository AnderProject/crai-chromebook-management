from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import Chromebook, Prestamo, Estudiante, Usuario as PerfilUsuario
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings
import unicodedata
import json
import uuid
import os

# Variable global temporal para guardar los tokens QR
qr_tokens = {}


@login_required
def portal(request):
    """Portal principal de módulos - Bienvenida"""
    contexto = {'titulo_pagina': 'Portal - CRAI UNEMI'}
    return render(request, 'prestamos/portal.html', contexto)


@login_required
def dashboard(request):
    """Vista principal del dashboard con datos reales"""
    from .models import Chromebook, Prestamo, Reserva, Notificacion
    
    # Obtener solo primer nombre y primer apellido
    primer_nombre = request.user.first_name.split()[0] if request.user.first_name else 'Admin'
    primer_apellido = request.user.last_name.split()[0] if request.user.last_name else 'CRAI'
    
    total_chromebooks = Chromebook.objects.count()
    disponibles = Chromebook.objects.filter(estado='disponible').count()
    prestados = Chromebook.objects.filter(estado='prestado').count()
    en_mantenimiento = Chromebook.objects.filter(estado='mantenimiento').count()
    porcentaje_disponible = round((disponibles / total_chromebooks) * 100) if total_chromebooks > 0 else 0
    
    prestamos_activos = Prestamo.objects.filter(estado='activo').count()
    ahora = timezone.now()
    manana = ahora + timedelta(hours=24)
    por_vencer = Prestamo.objects.filter(estado='activo', fecha_devolucion__lte=manana).count()
    vencidos = Prestamo.objects.filter(estado='vencido').count()
    
    total_estudiantes = User.objects.filter(groups__name='Estudiante').count()
    ultimos_prestamos = Prestamo.objects.select_related('estudiante', 'chromebook').all().order_by('-fecha_prestamo')[:5]
    notificaciones = Notificacion.objects.all().order_by('-fecha_envio')[:5]
    
    hoy = timezone.now().date()
    reservas_hoy = Reserva.objects.filter(fecha_uso=hoy, estado='pendiente').count()
    
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
        'primer_nombre': primer_nombre,
        'primer_apellido': primer_apellido,
    }
    return render(request, 'prestamos/dashboard.html', contexto)


@csrf_exempt
def api_devolver_prestamo(request):
    """API para registrar la devolución de un Chromebook"""
    if request.method == 'POST':
        data = json.loads(request.body)
        prestamo_id = data.get('prestamo_id')
        
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
    """Genera un token QR temporal para subir evidencia"""
    if request.method == 'POST':
        data = json.loads(request.body)
        reserva_id = data.get('reserva_id')
        
        token = str(uuid.uuid4())[:8]
        
        qr_tokens[token] = {
            'reserva_id': reserva_id,
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
        return render(request, 'prestamos/evidencia_expirada.html')
    
    data = qr_tokens[token]
    
    if data['expiracion'] < timezone.now():
        del qr_tokens[token]
        return render(request, 'prestamos/evidencia_expirada.html')
    
    if request.method == 'POST' and request.FILES.get('foto'):
        foto = request.FILES['foto']
        reserva_id = data.get('reserva_id')
        
        try:
            from .models import Reserva
            reserva = Reserva.objects.select_related('estudiante__usuario__user').get(id=reserva_id)
            nombre_completo = reserva.estudiante.usuario.user.get_full_name().replace(' ', '_')
            nombre_estudiante = unicodedata.normalize('NFKD', nombre_completo).encode('ASCII', 'ignore').decode('ASCII')
            codigo_reserva = reserva.codigo_verificacion
            nombre_archivo = f'{nombre_estudiante}_{codigo_reserva}.jpg'
        except:
            nombre_archivo = f'reserva_{reserva_id}_{token}.jpg'
        
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
        
        response = render(request, 'prestamos/evidencia_exitosa.html')
        response['ngrok-skip-browser-warning'] = 'true'
        return response
    
    response = render(request, 'prestamos/evidencia_subir.html', {'token': token})
    response['ngrok-skip-browser-warning'] = 'true'
    return response


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
    chromebooks = Chromebook.objects.all().order_by('codigo')
    total = chromebooks.count()
    disponibles = chromebooks.filter(estado='disponible').count()
    prestados = chromebooks.filter(estado='prestado').count()
    en_mantenimiento = chromebooks.filter(estado='mantenimiento').count()
    
    contexto = {
        'titulo_pagina': 'Chromebooks - CRAI UNEMI',
        'chromebooks': chromebooks, 'total': total,
        'disponibles': disponibles, 'prestados': prestados,
        'en_mantenimiento': en_mantenimiento,
    }
    return render(request, 'prestamos/chromebooks/lista.html', contexto)


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
            messages.success(request, '✅ Chromebook registrado exitosamente.')
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
                fecha_inicio=fecha_inicio,
                estado='en_proceso',
                registrado_por=request.user
            )
            
            # Actualizar estado del Chromebook
            chromebook.estado = 'mantenimiento'
            chromebook.save()
            
            messages.success(request, f'✅ {chromebook.codigo} enviado a mantenimiento.')
            return redirect('prestamos:lista_mantenimientos')
            
        except Chromebook.DoesNotExist:
            messages.error(request, 'Chromebook no encontrado.')
    
    chromebooks = Chromebook.objects.filter(estado__in=['disponible', 'prestado'])
    
    contexto = {
        'titulo_pagina': 'Agregar Mantenimiento - CRAI UNEMI',
        'chromebooks': chromebooks,
    }
    return render(request, 'prestamos/mantenimiento/agregar.html', contexto)


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
            
            # Devolver Chromebook a disponible
            chromebook = mantenimiento.chromebook
            chromebook.estado = 'disponible'
            chromebook.save()
            
            messages.success(request, f'✅ Mantenimiento finalizado. {chromebook.codigo} disponible.')
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
    disponibles = Chromebook.objects.filter(estado='disponible').count()
    hoy = timezone.now().date()
    prestamos_hoy = Prestamo.objects.filter(fecha_prestamo__date=hoy).select_related('estudiante', 'chromebook').order_by('-fecha_prestamo')
    total_hoy = prestamos_hoy.count()
    
    return render(request, 'prestamos/prestamos/registro_rapido.html', {
        'titulo_pagina': 'Registro Rápido - CRAI UNEMI',
        'disponibles': disponibles, 'prestamos_hoy': prestamos_hoy, 'total_hoy': total_hoy,
    })


@login_required
def lista_estudiantes(request):
    from .models import Reserva, Carrera
    
    estudiantes_con_prestamos = Prestamo.objects.values_list('estudiante_id', flat=True).distinct()
    estudiantes_con_reservas = Reserva.objects.values_list('estudiante__usuario__user_id', flat=True).distinct()
    usuarios_activos_ids = set(list(estudiantes_con_prestamos) + list(estudiantes_con_reservas))
    
    estudiantes = Estudiante.objects.select_related('usuario__user', 'carrera').filter(
        usuario__user__id__in=usuarios_activos_ids
    ).order_by('-usuario__user__date_joined')
    
    prestamos_activos_ids = list(Prestamo.objects.filter(estado='activo').values_list('estudiante_id', flat=True).distinct())
    
    contexto = {
        'titulo_pagina': 'Estudiantes - CRAI UNEMI',
        'estudiantes': estudiantes,
        'total_estudiantes': estudiantes.count(),
        'estudiantes_activos': estudiantes.filter(usuario__user__id__in=prestamos_activos_ids).count(),
        'vencidos': Prestamo.objects.filter(estado='vencido').count(),
        'prestamos_activos_ids': prestamos_activos_ids,
        'prestamos_activos_lista': Prestamo.objects.filter(estado='activo').select_related('estudiante', 'chromebook').order_by('fecha_devolucion')[:10],
        'prestamos_vencidos_lista': Prestamo.objects.filter(estado='vencido').select_related('estudiante', 'chromebook').order_by('-fecha_devolucion')[:10],
        'carreras': Carrera.objects.all(),
    }
    return render(request, 'prestamos/estudiantes/lista.html', contexto)


@csrf_exempt
def api_perfil_estudiante(request, id):
    try:
        estudiante = Estudiante.objects.select_related('usuario__user', 'carrera').get(id=id)
        user = estudiante.usuario.user
        
        prestamos = Prestamo.objects.filter(estudiante=user).select_related('chromebook').order_by('-fecha_prestamo')[:10]
        
        historial_html = ''
        for p in prestamos:
            fecha_str = p.fecha_prestamo.strftime("%d/%m/%Y") if p.fecha_prestamo else "-"
            color = 'text-success' if p.estado == 'devuelto' else ('text-danger' if p.estado == 'vencido' else 'text-warning')
            historial_html += f'<div class="small text-muted">{fecha_str} - {p.chromebook.codigo} • {p.duracion_horas}h • <span class="{color}">{p.estado}</span></div>'
        
        if not historial_html:
            historial_html = '<small class="text-muted">Sin historial de préstamos</small>'
        
        return JsonResponse({
            'avatar': f'{user.first_name[0].upper()}{user.last_name[0].upper()}',
            'nombre': user.get_full_name() or user.username,
            'cedula': estudiante.usuario.cedula,
            'carrera': estudiante.carrera.nombre,
            'semestre': estudiante.semestre,
            'email': user.email,
            'historial': historial_html,
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
            }})
        except Reserva.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Código no encontrado.'})
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


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
            
            if reserva.estado != 'pendiente':
                return JsonResponse({'success': False, 'message': 'Esta reserva ya fue procesada.'})
            
            chromebook = Chromebook.objects.filter(estado='disponible').first()
            
            if not chromebook:
                return JsonResponse({'success': False, 'message': 'No hay Chromebooks disponibles.'})
            
            prestamo = Prestamo.objects.create(
                estudiante=reserva.estudiante.usuario.user,
                chromebook=chromebook,
                reserva=reserva,
                fecha_devolucion=timezone.now() + timedelta(hours=reserva.calcular_duracion()),
                duracion_horas=reserva.calcular_duracion(),
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
            
            return JsonResponse({'success': True, 'data': {
                'id': chromebook.id, 'codigo': chromebook.codigo,
                'marca': chromebook.marca, 'modelo': chromebook.modelo,
                'estado': chromebook.estado, 'condicion': chromebook.condicion,
            }})
        except Chromebook.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Chromebook no encontrado.'})


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
            try:
                data_api = obtener_estudiante(cedula)
            except ApiEstudiantesError:
                return JsonResponse({'success': False, 'message': 'Servicio de matrículas no disponible. Intenta más tarde.'})
            if data_api:
                estudiante, _ = sincronizar_estudiante(data_api)

        if estudiante is None:
            return JsonResponse({'success': False, 'message': 'Estudiante no encontrado.'})

        perfil = estudiante.usuario
        return JsonResponse({'success': True, 'data': {
            'id': estudiante.id, 'user_id': perfil.user.id,
            'nombre': perfil.user.get_full_name() or perfil.user.username,
            'cedula': perfil.cedula,
            'carrera': estudiante.carrera.nombre if estudiante.carrera else 'No registrada',
            'semestre': estudiante.semestre,
        }})


@csrf_exempt
def api_registrar_prestamo(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        chromebook_id = data.get('chromebook_id')
        user_id = data.get('user_id')
        duracion = int(data.get('duracion', 4))
        
        try:
            chromebook = Chromebook.objects.get(id=chromebook_id)
            estudiante_user = User.objects.get(id=user_id)
            
            if chromebook.estado != 'disponible':
                return JsonResponse({'success': False, 'message': 'Este Chromebook no está disponible.'})
            
            import random, string
            caracteres = string.ascii_uppercase + string.digits
            codigo = ''.join(random.choices(caracteres, k=6))
            
            ahora = timezone.now()
            prestamo = Prestamo.objects.create(
                estudiante=estudiante_user, chromebook=chromebook,
                fecha_prestamo=ahora, fecha_devolucion=ahora + timedelta(hours=duracion),
                estado='activo', duracion_horas=duracion, codigo_verificacion=codigo,
            )
            
            chromebook.estado = 'prestado'
            chromebook.save()
            
            return JsonResponse({'success': True, 'message': f'Préstamo registrado. {chromebook.codigo} asignado.'})
            
        except Chromebook.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Chromebook no encontrado.'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Usuario no encontrado.'})
        




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
    return render(request, 'prestamos/ficha_estudiantil.html', contexto)




@login_required
def ajustes(request):
    """Página de configuración del sistema"""
    from .models import SesionUsuario
    
    sesiones = SesionUsuario.objects.filter(
        usuario=request.user
    ).order_by('-fecha_inicio')[:10]
    
    contexto = {
        'titulo_pagina': 'Ajustes - CRAI UNEMI',
        'sesiones': sesiones,
    }
    return render(request, 'prestamos/ajustes.html', contexto)



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
            cb = Chromebook.objects.get(id=id)
            cb.marca = data.get('marca', cb.marca)
            cb.modelo = data.get('modelo', cb.modelo)
            cb.serie = data.get('serie', cb.serie)
            cb.estado = data.get('estado', cb.estado)
            cb.condicion = data.get('condicion', cb.condicion)
            cb.notas = data.get('notas', cb.notas)
            cb.save()
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
        return render(request, 'prestamos/evidencia_expirada.html')
    
    data = qr_tokens[token]
    
    if data['expiracion'] < timezone.now():
        del qr_tokens[token]
        return render(request, 'prestamos/evidencia_expirada.html')
    
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
        
        response = render(request, 'prestamos/evidencia_exitosa.html')
        response['ngrok-skip-browser-warning'] = 'true'
        return response
    
    response = render(request, 'prestamos/evidencia_subir.html', {'token': token})
    response['ngrok-skip-browser-warning'] = 'true'
    return response