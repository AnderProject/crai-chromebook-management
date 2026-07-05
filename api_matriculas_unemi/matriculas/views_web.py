# -*- coding: utf-8 -*-
"""Interfaz web del simulador de matrículas.

Panel sencillo (sin login: es un simulador de tesis/demo) para REGISTRAR la
información que el sistema de reservas del CRAI necesita de cada estudiante:
cédula, nombres, correo institucional, teléfono, facultad, carrera, semestre
y estado de matrícula. También permite buscar, activar/desactivar y editar
el estado de matrícula de los ya registrados.
"""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect

from .models import EstudianteMatricula

# Catálogo base (los mismos usados por el sembrador de demo) para que el
# formulario ofrezca opciones consistentes con el sistema del CRAI.
FACULTADES = [
    'Facultad de Ciencias e Ingeniería',
    'Facultad de Ciencias Sociales, Educación Comercial y Derecho',
    'Facultad de Salud y Servicios Sociales',
    'Facultad de Educación',
]


def panel_matriculas(request):
    """Página principal: registro + listado con búsqueda."""

    if request.method == 'POST':
        accion = request.POST.get('accion', 'registrar')

        # ---- Activar / desactivar un estudiante ----
        if accion == 'toggle_activo':
            est = EstudianteMatricula.objects.filter(id=request.POST.get('id')).first()
            if est is None:
                messages.error(request, 'Estudiante no encontrado.')
            else:
                est.activo = not est.activo
                est.save(update_fields=['activo', 'actualizado'])
                estado = 'activado' if est.activo else 'desactivado'
                messages.success(request, f'{est.nombres} {est.apellidos} {estado} en la API.')
            return redirect('panel_matriculas')

        # ---- Cambiar el estado de matrícula ----
        if accion == 'cambiar_estado':
            est = EstudianteMatricula.objects.filter(id=request.POST.get('id')).first()
            nuevo = request.POST.get('estado_matricula', '')
            estados_validos = dict(EstudianteMatricula.ESTADOS_MATRICULA)
            if est is None:
                messages.error(request, 'Estudiante no encontrado.')
            elif nuevo not in estados_validos:
                messages.error(request, 'Estado de matrícula no válido.')
            else:
                est.estado_matricula = nuevo
                est.save(update_fields=['estado_matricula', 'actualizado'])
                messages.success(request, f'{est.nombres} {est.apellidos} ahora está {estados_validos[nuevo].lower()}.')
            return redirect('panel_matriculas')

        # ---- Registrar un estudiante nuevo ----
        cedula = (request.POST.get('cedula') or '').strip()
        nombres = (request.POST.get('nombres') or '').strip()
        apellidos = (request.POST.get('apellidos') or '').strip()
        correo = (request.POST.get('correo') or '').strip()
        telefono = (request.POST.get('telefono') or '').strip()
        facultad = (request.POST.get('facultad') or '').strip()
        carrera = (request.POST.get('carrera') or '').strip()
        semestre = (request.POST.get('semestre') or '').strip()
        estado_matricula = (request.POST.get('estado_matricula') or 'activo').strip()

        if not (cedula.isdigit() and len(cedula) == 10):
            messages.error(request, 'La cédula debe tener 10 dígitos.')
        elif EstudianteMatricula.objects.filter(cedula=cedula).exists():
            messages.error(request, f'Ya existe un estudiante matriculado con la cédula {cedula}.')
        elif not nombres or not apellidos:
            messages.error(request, 'Nombres y apellidos son obligatorios.')
        elif '@' not in correo:
            messages.error(request, 'Ingresa un correo institucional válido.')
        elif not facultad or not carrera:
            messages.error(request, 'Facultad y carrera son obligatorias.')
        elif not semestre.isdigit() or not (1 <= int(semestre) <= 10):
            messages.error(request, 'El semestre debe ser un número entre 1 y 10.')
        else:
            EstudianteMatricula.objects.create(
                cedula=cedula, nombres=nombres, apellidos=apellidos,
                correo=correo, telefono=telefono[:10],
                facultad=facultad, carrera=carrera, semestre=int(semestre),
                estado_matricula=estado_matricula,
            )
            messages.success(
                request,
                f'Estudiante {nombres} {apellidos} matriculado. El CRAI ya puede '
                f'verificarlo y sincronizarlo con la cédula {cedula}.'
            )
        return redirect('panel_matriculas')

    # ---- Listado con búsqueda ----
    q = (request.GET.get('q') or '').strip()
    estudiantes = EstudianteMatricula.objects.all()
    if q:
        estudiantes = estudiantes.filter(
            Q(cedula__icontains=q) | Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) | Q(carrera__icontains=q)
        )

    total = EstudianteMatricula.objects.count()
    activos = EstudianteMatricula.objects.filter(activo=True, estado_matricula='activo').count()
    inactivos = total - EstudianteMatricula.objects.filter(activo=True).count()

    # Carreras ya usadas (para sugerirlas en el formulario)
    carreras_existentes = (EstudianteMatricula.objects
                           .order_by('carrera').values_list('carrera', flat=True).distinct())

    contexto = {
        'estudiantes': estudiantes[:200],
        'q': q,
        'total': total,
        'activos': activos,
        'inactivos': inactivos,
        'facultades': FACULTADES,
        'carreras_existentes': carreras_existentes,
        'estados': EstudianteMatricula.ESTADOS_MATRICULA,
    }
    return render(request, 'matriculas/panel.html', contexto)
