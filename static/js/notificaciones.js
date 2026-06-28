// Modal de notificaciones del dashboard.
// Al abrirlo: marca todas como leidas en el servidor y sincroniza el numerito
// rojo de la campana (lo oculta) y el resaltado de "no leida" del modal.
(function () {
    var modal = document.getElementById('modalNotificaciones');
    if (!modal) return;

    modal.addEventListener('shown.bs.modal', function () {
        fetch('/notificaciones/marcar-leidas/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json'
            }
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (!data || !data.ok) return;

            // Oculta el numerito rojo de la campana.
            var badge = document.querySelector('.notificacion-badge');
            if (badge) badge.style.display = 'none';

            // Quita el resaltado de "no leida" y los puntitos dentro del modal.
            modal.querySelectorAll('.notif-no-leida').forEach(function (el) {
                el.classList.remove('notif-no-leida');
            });
            modal.querySelectorAll('.notif-item-punto').forEach(function (el) {
                el.remove();
            });
        })
        .catch(function () { /* sin conexion: se reintenta al reabrir */ });
    });

    function getCSRFToken() {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var c = cookies[i].trim();
            if (c.startsWith('csrftoken=')) return c.substring('csrftoken='.length);
        }
        return '';
    }
})();
