from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def portal(request):
    """Portal principal de módulos - Bienvenida"""
    contexto = {
        'titulo_pagina': 'Portal - CRAI UNEMI'
    }
    return render(request, 'prestamos/portal.html', contexto)


@login_required
def dashboard(request):
    """Vista principal del dashboard"""
    contexto = {
        'titulo_pagina': 'Dashboard - CRAI UNEMI'
    }
    return render(request, 'prestamos/dashboard.html', contexto)



@login_required
def lista_chromebooks(request):
    """Vista de inventario de Chromebooks"""
    contexto = {
        'titulo_pagina': 'Chromebooks - CRAI UNEMI'
    }
    return render(request, 'prestamos/chromebooks/lista.html', contexto)


@login_required
def detalle_chromebook(request, pk):
    """Vista de detalle de un Chromebook"""
    contexto = {
        'titulo_pagina': 'Detalle Chromebook - CRAI UNEMI'
    }
    return render(request, 'prestamos/chromebooks/detalle.html', contexto)


@login_required
def agregar_chromebook(request):
    """Vista para agregar un nuevo Chromebook"""
    contexto = {
        'titulo_pagina': 'Agregar Chromebook - CRAI UNEMI'
    }
    return render(request, 'prestamos/chromebooks/agregar.html', contexto)



@login_required
def registro_rapido(request):
    """Sistema de registro rápido de préstamos"""
    
    # Datos simulados del estudiante (cuando se busque por cédula)
    estudiante_encontrado = None
    chromebook_seleccionado = None
    
    if request.method == 'POST':
        # Aquí irá la lógica de préstamo
        pass
    
    contexto = {
        'titulo_pagina': 'Registro Rápido - CRAI UNEMI',
    }
    return render(request, 'prestamos/prestamos/registro_rapido.html', contexto)




@login_required
def lista_estudiantes(request):
    """Vista principal de estudiantes con pestañas"""
    contexto = {
        'titulo_pagina': 'Estudiantes - CRAI UNEMI',
        'pestana_activa': request.GET.get('tab', 'directorio'),
    }
    return render(request, 'prestamos/estudiantes/lista.html', contexto)