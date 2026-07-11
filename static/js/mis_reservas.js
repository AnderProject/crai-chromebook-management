// Las reservas ahora se muestran todas y se deslizan con scroll dentro del panel
// (.reservas-scroll), sin paginación.
document.addEventListener('DOMContentLoaded', function() {
    actualizarProgresos();
    // Cada segundo, para que el reloj de cuenta regresiva "baje" en vivo.
    setInterval(actualizarProgresos, 1000);
});

// Formatea milisegundos como reloj de cuenta regresiva (H:MM:SS o MM:SS).
function formatoCuenta(ms) {
    var s = Math.floor(ms / 1000);
    var h = Math.floor(s / 3600); s %= 3600;
    var m = Math.floor(s / 60); s %= 60;
    var mm = (m < 10 ? '0' : '') + m;
    var ss = (s < 10 ? '0' : '') + s;
    return h > 0 ? (h + ':' + mm + ':' + ss) : (mm + ':' + ss);
}

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
        prog.classList.remove('por-terminar', 'terminado');
        if (ahora < dInicio) {
            // Aún no inicia: cuenta regresiva para empezar.
            tiempo.textContent = 'Inicia en ' + formatoCuenta(dInicio - ahora);
        } else {
            var restante = dFin - ahora;
            if (restante <= 0) {
                tiempo.textContent = 'Finalizado';
                prog.classList.add('terminado');
            } else {
                tiempo.textContent = 'Quedan ' + formatoCuenta(restante);
                // Últimos 5 minutos: se resalta en rojo (urgencia).
                if (restante <= 5 * 60000) prog.classList.add('por-terminar');
            }
        }
    });
}
// ===== Filtros por estado en "Mis Reservas" =====
// Al abrir, se ubica por defecto en "Pendientes"; si una sección no tiene
// reservas, muestra un estado vacío con ícono en vez de una lista en blanco.
(function () {
    var cont = document.getElementById('reservasFiltros');
    if (!cont) return;
    var chips = cont.querySelectorAll('.filtro-chip');
    var cards = document.querySelectorAll('#reservasGrid [data-estado]');
    var vacio = document.getElementById('reservasVacioFiltro');

    // Texto/ícono del estado vacío según la sección activa.
    var VACIO = {
        todas:      { i: 'bi-inbox',                  t: 'Sin reservas',            p: 'Todavía no tienes reservas registradas.' },
        pendiente:  { i: 'bi-hourglass-split',        t: 'Sin reservas pendientes', p: 'Aquí aparecerán tus reservas pendientes.' },
        completada: { i: 'bi-check-circle',           t: 'Sin completadas',         p: 'Aún no tienes reservas completadas.' },
        vencida:    { i: 'bi-exclamation-triangle',   t: 'Sin vencidas',            p: '¡Bien! No tienes reservas vencidas.' },
        cancelada:  { i: 'bi-x-circle',               t: 'Sin canceladas',          p: 'No has cancelado ninguna reserva.' }
    };

    function aplicarFiltro(filtro) {
        var visibles = 0;
        cards.forEach(function (card) {
            var ok = filtro === 'todas' || card.getAttribute('data-estado') === filtro;
            card.classList.toggle('filtro-oculta', !ok);
            if (ok) visibles++;
        });
        if (vacio) {
            var info = VACIO[filtro] || VACIO.todas;
            vacio.querySelector('.rvf-icono i').className = 'bi ' + info.i;
            vacio.querySelector('.rvf-titulo').textContent = info.t;
            vacio.querySelector('.rvf-texto').textContent = info.p;
            vacio.style.display = (visibles === 0) ? '' : 'none';
        }
    }

    chips.forEach(function (chip) {
        chip.addEventListener('click', function () {
            chips.forEach(function (c) { c.classList.remove('activo'); });
            chip.classList.add('activo');
            aplicarFiltro(chip.getAttribute('data-filtro'));
        });
    });

    // Estado inicial: el chip marcado como activo (Pendientes por defecto).
    var inicial = cont.querySelector('.filtro-chip.activo') || chips[0];
    if (inicial) aplicarFiltro(inicial.getAttribute('data-filtro'));
})();
