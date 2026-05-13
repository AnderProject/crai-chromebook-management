from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import random


@login_required
def portal_estudiante(request):
    """Portal principal del estudiante"""
    contexto = {
        'titulo_pagina': 'Portal Estudiante - CRAI UNEMI'
    }
    return render(request, 'estudiantes/portal.html', contexto)


@login_required
def reservar_chromebook(request):
    """Vista para reservar un Chromebook"""
    codigo_verificacion = None
    
    if request.method == 'POST':
        codigo_verificacion = random.randint(100000, 999999)
        messages.success(request, f'✅ Reserva registrada. Tu código es: {codigo_verificacion}')
    
    contexto = {
        'titulo_pagina': 'Reservar Chromebook - CRAI UNEMI',
        'codigo': codigo_verificacion,
    }
    return render(request, 'estudiantes/reservar.html', contexto)


@login_required
def mis_reservas(request):
    """Historial de reservas del estudiante"""
    contexto = {
        'titulo_pagina': 'Mis Reservas - CRAI UNEMI'
    }
    return render(request, 'estudiantes/mis_reservas.html', contexto)