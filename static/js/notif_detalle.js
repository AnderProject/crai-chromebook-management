// Notificaciones del dashboard: al hacer clic en una notificacion del menu de la
// campana se abre un modal con su detalle, se marca como leida y baja el numero.
(function () {
    var modal = document.getElementById('notifDetalleModal');
    if (!modal) return;

    var elTitulo = modal.querySelector('.notifd-titulo');
    var elTipo = modal.querySelector('.notifd-tipo');
    var elFecha = modal.querySelector('.notifd-fecha');
    var elMsg = modal.querySelector('.notifd-msg');
    var elIcono = modal.querySelector('.notifd-icono i');

    var ICONOS = { prestamo: 'bi-laptop', vencimiento: 'bi-exclamation-triangle', reserva: 'bi-calendar-check', general: 'bi-bell-fill' };
    var TIPOS = { prestamo: 'Préstamo', vencimiento: 'Vencimiento', reserva: 'Reserva', general: 'General' };

    function abrir(item) {
        var tipo = item.getAttribute('data-notif-tipo') || 'general';
        elTitulo.textContent = item.getAttribute('data-notif-titulo') || '';
        elMsg.textContent = item.getAttribute('data-notif-msg') || '';
        elFecha.textContent = item.getAttribute('data-notif-fecha') || '';
        elTipo.textContent = TIPOS[tipo] || 'Notificación';
        elIcono.className = 'bi ' + (ICONOS[tipo] || 'bi-bell-fill');
        modal.classList.add('visible');
        if (item.getAttribute('data-notif-leida') === '0') marcarLeida(item);
    }

    function marcarLeida(item) {
        var id = item.getAttribute('data-notif-id');
        fetch('/notificaciones/marcar-leida/' + id + '/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken(), 'Content-Type': 'application/json' }
        })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (!d || !d.ok) return;
            item.setAttribute('data-notif-leida', '1');
            item.classList.remove('notif-drop-no-leida');
            item.classList.add('notif-drop-leida');
            var badge = document.querySelector('.notificacion-badge');
            if (badge) {
                if (d.total_no_leidas > 0) { badge.textContent = d.total_no_leidas; }
                else { badge.style.display = 'none'; }
            }
        })
        .catch(function () {});
    }

    function cerrar() { modal.classList.remove('visible'); }

    document.querySelectorAll('.notif-drop-item').forEach(function (item) {
        item.addEventListener('click', function (e) { e.preventDefault(); abrir(item); });
    });
    modal.addEventListener('click', function (e) { if (e.target === modal) cerrar(); });
    var btnCerrar = modal.querySelector('.notifd-cerrar');
    if (btnCerrar) btnCerrar.addEventListener('click', cerrar);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') cerrar(); });

    function getCSRFToken() {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var c = cookies[i].trim();
            if (c.startsWith('csrftoken=')) return c.substring('csrftoken='.length);
        }
        return '';
    }
})();
