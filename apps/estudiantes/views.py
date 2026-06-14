from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import random


@login_required
def portal_estudiante(request):
    """Portal principal del estudiante con datos reales"""
    from apps.prestamos.models import Chromebook, Reserva, Prestamo, Estudiante, Usuario as PerfilUsuario
    from django.utils import timezone
    
    # Disponibilidad real
    total_chromebooks = Chromebook.objects.count()
    disponibles = Chromebook.objects.filter(estado='disponible').count()
    
    # Actividad reciente del estudiante
    actividad = []
    
    try:
        perfil = PerfilUsuario.objects.get(user=request.user)
        estudiante = Estudiante.objects.get(usuario=perfil)
        
        # Préstamos activos
        prestamos_activos = Prestamo.objects.filter(
            estudiante=request.user,
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
            estudiante=request.user,
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
    
    contexto = {
        'titulo_pagina': 'Portal Estudiante - CRAI UNEMI',
        'total_chromebooks': total_chromebooks,
        'disponibles': disponibles,
        'actividad': actividad,
    }
    return render(request, 'estudiantes/portal.html', contexto)

@login_required
def reservar_chromebook(request):
    """Vista para reservar un Chromebook"""
    from apps.prestamos.models import Reserva, Estudiante, Carrera, Chromebook
    from apps.prestamos.models import Usuario as PerfilUsuario, TipoUsuario
    from apps.prestamos.models import Notificacion
    from django.http import JsonResponse
    from datetime import datetime, timedelta
    import random
    import string
    
    # Si es GET, mostrar el formulario con datos reales
    if request.method == 'GET':
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
            duracion = int(request.POST.get('duracion', 4))
            motivo = request.POST.get('motivo', '')
            fecha_uso = request.POST.get('fecha_uso', '')
            hora_inicio = request.POST.get('hora_inicio', '08:00')
            
            usuario = request.user
            
            tipo_estudiante, _ = TipoUsuario.objects.get_or_create(nombre='Estudiante')
            perfil, _ = PerfilUsuario.objects.get_or_create(
                user=usuario,
                defaults={
                    'tipo_usuario': tipo_estudiante,
                    'cedula': 'Sin registrar',
                    'telefono': 'Sin registrar'
                }
            )
            
            carrera = Carrera.objects.first()
            estudiante, _ = Estudiante.objects.get_or_create(
                usuario=perfil,
                defaults={'carrera': carrera, 'semestre': 1}
            )
            
            caracteres = string.ascii_uppercase + string.digits
            while True:
                codigo = ''.join(random.choices(caracteres, k=6))
                if not Reserva.objects.filter(codigo_verificacion=codigo).exists():
                    break
            
            hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M').time()
            hora_fin_dt = (datetime.combine(datetime.today(), hora_inicio_dt) + timedelta(hours=duracion)).time()
            
            fecha = datetime.strptime(fecha_uso, '%Y-%m-%d').date() if fecha_uso else datetime.now().date()
            
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