// Notificaciones del dashboard: al hacer clic en una notificacion de la campana
// se abre un modal con su detalle (y el de la reserva asociada, si existe), se
// marca como leida en el servidor y el numerito rojo se sincroniza.
(function () {
    var modal = document.getElementById('notifDetalleModal');
    if (!modal) return;

    var elTitulo = modal.querySelector('.notifd-titulo');
    var elTipo = modal.querySelector('.notifd-tipo');
    var elFecha = modal.querySelector('.notifd-fecha');
    var elMsg = modal.querySelector('.notifd-msg');
    var elIcono = modal.querySelector('.notifd-icono i');
    var elReserva = document.getElementById('notifdReserva');

    var ICONOS = { prestamo: 'bi-laptop', vencimiento: 'bi-exclamation-triangle', reserva: 'bi-calendar-check', general: 'bi-bell-fill' };
    var TIPOS = { prestamo: 'Préstamo', vencimiento: 'Vencimiento', reserva: 'Reserva', general: 'General' };
    // Colores del badge de estado de la reserva dentro del modal
    var ESTADOS = {
        pendiente: 'notifd-est-pendiente',
        confirmada: 'notifd-est-ok',
        completada: 'notifd-est-ok',
        cancelada: 'notifd-est-mal',
        vencida: 'notifd-est-mal'
    };

    function abrir(item) {
        var id = item.getAttribute('data-notif-id');
        var tipo = item.getAttribute('data-notif-tipo') || 'general';

        // Pintamos lo que ya sabemos (respuesta instantánea) y pedimos el detalle.
        elTitulo.textContent = item.getAttribute('data-notif-titulo') || '';
        elMsg.textContent = item.getAttribute('data-notif-msg') || '';
        elFecha.textContent = item.getAttribute('data-notif-fecha') || '';
        elTipo.textContent = TIPOS[tipo] || 'Notificación';
        elIcono.className = 'bi ' + (ICONOS[tipo] || 'bi-bell-fill');
        elReserva.hidden = true;
        modal.classList.add('visible');

        fetch('/prestamos/notificaciones/detalle/' + id + '/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (!d || !d.ok) return;

            // La notificación quedó leída en el servidor: reflejar en la lista + badge.
            item.setAttribute('data-notif-leida', '1');
            item.classList.remove('notif-drop-no-leida');
            item.classList.add('notif-drop-leida');
            actualizarBadge(d.total_no_leidas);

            // Detalle de la reserva asociada (si existe).
            if (d.reserva) {
                var r = d.reserva;
                poner('codigo', r.codigo);
                poner('estudiante', r.estudiante);
                poner('cedula', r.cedula || '—');
                poner('fecha_uso', r.fecha_uso);
                poner('horario', r.horario);
                poner('equipo', r.equipo);
                poner('carrera', r.carrera || '—');
                var estadoEl = elReserva.querySelector('[data-campo="estado"]');
                estadoEl.textContent = r.estado;
                estadoEl.className = 'notifd-reserva-estado ' + (ESTADOS[r.estado_raw] || '');
                elReserva.hidden = false;
            }
        })
        .catch(function () {});
    }

    function poner(campo, valor) {
        var el = elReserva.querySelector('[data-campo="' + campo + '"]');
        if (el) el.textContent = valor || '—';
    }

    function actualizarBadge(total) {
        var badge = document.querySelector('.notificacion-badge');
        if (!badge) return;
        if (total > 0) {
            badge.textContent = total;
            badge.style.display = '';
        } else {
            badge.style.display = 'none';
        }
    }

    function cerrar() { modal.classList.remove('visible'); }

    document.querySelectorAll('.notif-drop-item').forEach(function (item) {
        item.addEventListener('click', function (e) { e.preventDefault(); abrir(item); });
    });
    modal.addEventListener('click', function (e) { if (e.target === modal) cerrar(); });
    var btnCerrar = modal.querySelector('.notifd-cerrar');
    if (btnCerrar) btnCerrar.addEventListener('click', cerrar);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') cerrar(); });
})();
