// =============================================
// MODO OSCURO - GLOBAL
// =============================================
function toggleModoOscuro() {
    var activo = document.getElementById('modoOscuro').checked;
    
    if (activo) {
        document.body.classList.add('modo-oscuro');
        localStorage.setItem('modoOscuro', 'true');
    } else {
        document.body.classList.remove('modo-oscuro');
        localStorage.setItem('modoOscuro', 'false');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('modoOscuro') === 'true') {
        document.body.classList.add('modo-oscuro');
        var checkbox = document.getElementById('modoOscuro');
        if (checkbox) checkbox.checked = true;
    }
});

// =============================================
// SIDEBAR MÓVIL - GLOBAL
// Botón flotante para abrir/cerrar el menú lateral en pantallas chicas.
// Solo se añade en páginas del panel admin (las que tienen #sidebarMenu).
// =============================================
document.addEventListener('DOMContentLoaded', function () {
    var sidebar = document.getElementById('sidebarMenu');
    if (!sidebar || typeof bootstrap === 'undefined') { return; }

    var boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'btn-sidebar-movil';
    boton.setAttribute('aria-label', 'Abrir o cerrar menú');
    boton.innerHTML = '<i class="bi bi-list"></i>';
    document.body.appendChild(boton);

    var collapse = bootstrap.Collapse.getOrCreateInstance(sidebar, { toggle: false });
    boton.addEventListener('click', function () { collapse.toggle(); });

    // En móvil, cerrar el menú al elegir una opción (mejor UX).
    sidebar.querySelectorAll('.nav-link').forEach(function (link) {
        link.addEventListener('click', function () {
            if (window.matchMedia('(max-width: 767.98px)').matches) { collapse.hide(); }
        });
    });
});