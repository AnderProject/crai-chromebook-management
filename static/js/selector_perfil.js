// =============================================
// SELECTOR DE PERFIL - CRAI UNEMI
// Navegación dinámica sin recargar
// =============================================

function mostrarLogin(tipo) {
    // Ocultar selector
    document.getElementById('vista-selector').classList.remove('vista-activa');
    document.getElementById('vista-selector').classList.add('vista-oculta');
    
    // Mostrar login correspondiente
    if (tipo === 'estudiante') {
        document.getElementById('vista-login-estudiante').classList.remove('vista-oculta');
        document.getElementById('vista-login-estudiante').classList.add('vista-activa');
    } else if (tipo === 'administrador') {
        document.getElementById('vista-login-admin').classList.remove('vista-oculta');
        document.getElementById('vista-login-admin').classList.add('vista-activa');
    } else if (tipo === 'recepcionista') {
        document.getElementById('vista-login-recepcionista').classList.remove('vista-oculta');
        document.getElementById('vista-login-recepcionista').classList.add('vista-activa');
    }
}

function volverSelector() {
    // Ocultar logins
    ['vista-login-estudiante', 'vista-login-admin', 'vista-login-recepcionista'].forEach(function (id) {
        var el = document.getElementById(id);
        if (!el) return;
        el.classList.remove('vista-activa');
        el.classList.add('vista-oculta');
    });

    // Mostrar selector
    document.getElementById('vista-selector').classList.remove('vista-oculta');
    document.getElementById('vista-selector').classList.add('vista-activa');
}

// Si el servidor indica abrir una vista (p. ej. tras error de login), se abre
// automáticamente el formulario correspondiente con el error ya visible.
document.addEventListener('DOMContentLoaded', function () {
    var panel = document.getElementById('panelDinamico');
    var abrir = panel ? panel.dataset.abrir : '';
    if (abrir === 'estudiante' || abrir === 'administrador' || abrir === 'recepcionista') {
        mostrarLogin(abrir);
    }
});
