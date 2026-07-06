// Las reservas ahora se muestran todas y se deslizan con scroll dentro del panel
// (.reservas-scroll), sin paginación.
document.addEventListener('DOMContentLoaded', function() {
    actualizarProgresos();
    setInterval(actualizarProgresos, 30000);
});

// =============================================
// CANCELAR RESERVA
// =============================================
var idReservaCancelar = null;

// Abre el modal de confirmación (en vez del confirm() del navegador).
function cancelarReserva(id) {
    idReservaCancelar = id;
    var modal = document.getElementById('modalCancelar');
    if (modal) modal.classList.add('visible');
}

function cerrarModalCancelar() {
    var modal = document.getElementById('modalCancelar');
    if (modal) modal.classList.remove('visible');
    idReservaCancelar = null;
}

function confirmarCancelacion() {
    if (!idReservaCancelar) return;
    var id = idReservaCancelar;
    var btn = document.getElementById('btnConfirmarCancelar');
    if (btn) { btn.disabled = true; btn.textContent = 'Cancelando...'; }

    fetch('/estudiantes/api/cancelar-reserva/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ reserva_id: id })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (data.success) {
            mostrarToastTrasReload('Reserva cancelada', 'success');
            location.reload();
        } else {
            cerrarModalCancelar();
            mostrarToast(data.message || 'No se pudo cancelar la reserva.', 'error');
            if (btn) { btn.disabled = false; btn.textContent = 'Sí, cancelar'; }
        }
    })
    .catch(function () {
        cerrarModalCancelar();
        mostrarToast('Error de conexión. Intenta de nuevo.', 'error');
        if (btn) { btn.disabled = false; btn.textContent = 'Sí, cancelar'; }
    });
}

function getCookie(name) {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.startsWith(name + '=')) return c.substring(name.length + 1);
    }
    return '';
}

function actualizarProgresos() {
    document.querySelectorAll('.progreso-live').forEach(function(prog) {
        var ahora = new Date();
        var fecha = prog.getAttribute('data-fecha');
        var inicio = prog.getAttribute('data-inicio');
        var fin = prog.getAttribute('data-fin');
        if (!fecha || !inicio || !fin) return;

        // Construir las fechas completas usando el día de uso de la reserva,
        // no el día actual (de lo contrario una reserva futura salía "Vencido").
        var pf2 = fecha.split('-');
        var pi = inicio.split(':'), pf = fin.split(':');
        var dInicio = new Date(pf2[0], pf2[1] - 1, pf2[2], pi[0], pi[1], 0, 0);
        var dFin = new Date(pf2[0], pf2[1] - 1, pf2[2], pf[0], pf[1], 0, 0);

        var total = dFin - dInicio, trans = ahora - dInicio;
        var pct = Math.min(100, Math.max(0, (trans / total) * 100));

        prog.querySelector('.progreso-live-fill').style.width = pct + '%';

        var tiempo = prog.querySelector('.progreso-live-time');
        if (ahora < dInicio) {
            // Aún no inicia: mostrar cuánto falta para empezar.
            var faltan = dInicio - ahora;
            var dh = Math.floor(faltan / 3600000), dm = Math.floor((faltan % 3600000) / 60000);
            tiempo.textContent = 'Inicia en ' + (dh > 0 ? dh + 'h ' : '') + dm + 'm';
        } else {
            var restante = dFin - ahora;
            if (restante <= 0) { tiempo.textContent = 'Finalizado'; }
            else {
                var h = Math.floor(restante / 3600000), m = Math.floor((restante % 3600000) / 60000);
                tiempo.textContent = h + 'h ' + m + 'm';
            }
        }
    });
}
// ===== Filtros por estado en "Mis Reservas" =====
(function () {
    var cont = document.getElementById('reservasFiltros');
    if (!cont) return;
    var chips = cont.querySelectorAll('.filtro-chip');
    var cards = document.querySelectorAll('.reserva-card-compact');

    chips.forEach(function (chip) {
        chip.addEventListener('click', function () {
            chips.forEach(function (c) { c.classList.remove('activo'); });
            chip.classList.add('activo');
            var filtro = chip.getAttribute('data-filtro');
            cards.forEach(function (card) {
                var visible = filtro === 'todas' || card.getAttribute('data-estado') === filtro;
                card.classList.toggle('filtro-oculta', !visible);
            });
        });
    });
})();
