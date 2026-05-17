// =============================================
// ESTUDIANTES - CRAI UNEMI
// Pestañas, modal y navegación
// =============================================

function cambiarTab(tab) {
    // Quitar activo de todos los botones
    document.querySelectorAll('.tab-btn').forEach(function(b) {
        b.classList.remove('active');
    });
    
    // Activar el botón clickeado
    event.target.classList.add('active');
    
    // Ocultar todos los tabs
    document.getElementById('tab-directorio').style.display = 'none';
    document.getElementById('tab-monitoreo').style.display = 'none';
    document.getElementById('tab-registro').style.display = 'none';
    
    // Mostrar el tab seleccionado
    if (tab === 'directorio') {
        document.getElementById('tab-directorio').style.display = 'block';
    } else if (tab === 'monitoreo') {
        document.getElementById('tab-monitoreo').style.display = 'block';
    } else if (tab === 'registro') {
        document.getElementById('tab-registro').style.display = 'block';
    }
}

function abrirPerfil(nombre) {
    document.getElementById('modalPerfil').classList.add('abierto');
    document.getElementById('overlay').classList.add('visible');
}

function cerrarPerfil() {
    document.getElementById('modalPerfil').classList.remove('abierto');
    document.getElementById('overlay').classList.remove('visible');
}

function mostrarRegistro() {
    cambiarTab('registro');
    document.querySelectorAll('.tab-btn').forEach(function(b) {
        b.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn')[2].classList.add('active');
}