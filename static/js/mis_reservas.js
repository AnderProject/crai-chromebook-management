var paginaActual = 1;
var tarjetasPorPagina = 6;

document.addEventListener('DOMContentLoaded', function() {
    inicializarPaginacion();
    actualizarProgresos();
    setInterval(actualizarProgresos, 30000);
});

function inicializarPaginacion() {
    var tarjetas = document.querySelectorAll('.reserva-card-compact');
    var totalPaginas = Math.ceil(tarjetas.length / tarjetasPorPagina);
    
    if (totalPaginas <= 1) {
        document.getElementById('paginacionReservas').style.display = 'none';
        return;
    }
    
    var numsHtml = '';
    for (var i = 1; i <= totalPaginas; i++) {
        numsHtml += '<button class="btn-pag' + (i === 1 ? ' activo' : '') + '" onclick="irPagina(' + i + ')">' + i + '</button>';
    }
    document.getElementById('paginasNumeros').innerHTML = numsHtml;
    mostrarPagina(1);
}

function mostrarPagina(pagina) {
    var tarjetas = document.querySelectorAll('.reserva-card-compact');
    var inicio = (pagina - 1) * tarjetasPorPagina;
    var fin = inicio + tarjetasPorPagina;
    
    tarjetas.forEach(function(t, i) {
        t.style.display = (i >= inicio && i < fin) ? 'flex' : 'none';
    });
    paginaActual = pagina;
    
    document.querySelectorAll('.pag-nums .btn-pag').forEach(function(b) { b.classList.remove('activo'); });
    var botones = document.querySelectorAll('.pag-nums .btn-pag');
    if (botones[pagina - 1]) botones[pagina - 1].classList.add('activo');
    
    document.getElementById('btnAnterior').disabled = pagina <= 1;
    document.getElementById('btnSiguiente').disabled = pagina >= Math.ceil(tarjetas.length / tarjetasPorPagina);
}

function irPagina(p) { mostrarPagina(p); }

function cambiarPagina(dir) {
    var total = Math.ceil(document.querySelectorAll('.reserva-card-compact').length / tarjetasPorPagina);
    if (dir === 'anterior' && paginaActual > 1) mostrarPagina(paginaActual - 1);
    if (dir === 'siguiente' && paginaActual < total) mostrarPagina(paginaActual + 1);
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