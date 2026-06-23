// =============================================
// ACTUALIZACIÓN EN VIVO (ADMIN) - CRAI UNEMI
// Polling ligero por sección. Se auto-inicia según las anclas presentes en el DOM.
// =============================================

var REALTIME_INTERVALO = 8000; // 8s (chromebooks, monitoreo, registro rápido)
var REALTIME_DASHBOARD = 5000; // 5s: el dashboard refresca reservaciones casi al momento

function craiObtener(url) {
    return fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (r) { return r.json(); });
}

// Actualiza todos los <... data-stat="clave"> con el valor del mapa de contadores
function actualizarContadores(contadores) {
    if (!contadores) return;
    Object.keys(contadores).forEach(function (clave) {
        var nodos = document.querySelectorAll('[data-stat="' + clave + '"]');
        nodos.forEach(function (n) { n.textContent = contadores[clave]; });
    });
}

// Memoria del último HTML pintado: solo se reemplaza el DOM si CAMBIÓ (evita el parpadeo)
var ultimoDashboardHtml = null;
var ultimoPrestamosHoyHtml = null;
var ultimoReservasHtml = null;

// ¿Hay una interacción en curso en la tabla de reservas que NO debemos pisar?
// (un código revelado, un input de cédula abierto, o una búsqueda activa)
function reservasOcupado() {
    var tbody = document.getElementById('tbodyReservasPendientes');
    if (!tbody) { return false; }
    if (tbody.querySelector('.cedula-inline, .codigo-revelado')) { return true; }
    var buscador = document.getElementById('buscadorReservas');
    if (buscador && buscador.value.trim() !== '') { return true; }
    return false;
}

// ---- Dashboard: contadores + tabla últimos préstamos + reservas pendientes ----
function pollDashboard() {
    craiObtener('/prestamos/api/dashboard-stats/')
        .then(function (data) {
            actualizarContadores(data.contadores);
            var tbody = document.getElementById('tbodyUltimosPrestamos');
            if (tbody && data.filas_html && data.filas_html !== ultimoDashboardHtml) {
                tbody.innerHTML = data.filas_html;
                ultimoDashboardHtml = data.filas_html;
                if (typeof actualizarTiemposRestantes === 'function') {
                    actualizarTiemposRestantes();
                }
            }

            // Tabla de Reservaciones Pendientes (no pisar interacciones en curso)
            var tbodyReservas = document.getElementById('tbodyReservasPendientes');
            if (tbodyReservas && data.reservas_html && data.reservas_html !== ultimoReservasHtml && !reservasOcupado()) {
                tbodyReservas.innerHTML = data.reservas_html;
                ultimoReservasHtml = data.reservas_html;
                var badge = document.getElementById('badgeReservasPendientes');
                if (badge && data.contadores && typeof data.contadores.reservas_pendientes !== 'undefined') {
                    badge.textContent = data.contadores.reservas_pendientes;
                }
            }
        })
        .catch(function () { /* silencioso */ });
}

// ---- Registro rápido: lista de préstamos de hoy ----
function pollPrestamosHoy() {
    craiObtener('/prestamos/api/prestamos-hoy/')
        .then(function (data) {
            var lista = document.getElementById('listaPrestamosHoy');
            if (lista && data.html && data.html !== ultimoPrestamosHoyHtml) {
                lista.innerHTML = data.html;
                ultimoPrestamosHoyHtml = data.html;
            }
            actualizarContadores({ total_hoy: data.total_hoy });
        })
        .catch(function () { /* silencioso */ });
}

// ---- Chromebooks: contadores + badge de estado por fila (preserva el filtro) ----
var CB_BADGES = {
    disponible: { clase: 'bg-success', texto: 'Disponible' },
    pendiente_reserva: { clase: 'bg-pendiente', texto: 'Pendiente a reserva' },
    prestado: { clase: 'bg-warning', texto: 'Prestado' },
    mantenimiento: { clase: 'bg-danger', texto: 'Mantenimiento' }
};

function pollChromebooks() {
    craiObtener('/prestamos/api/chromebooks-estado/')
        .then(function (data) {
            actualizarContadores(data.contadores);
            if (!data.estados) return;
            Object.keys(data.estados).forEach(function (codigo) {
                var estado = data.estados[codigo];
                var fila = document.querySelector('tr[data-codigo="' + codigo.toLowerCase() + '"]');
                if (!fila) return;
                // Solo tocar la fila si el estado CAMBIÓ (evita el parpadeo del badge)
                if (fila.getAttribute('data-estado') === estado) return;
                fila.setAttribute('data-estado', estado);
                var celda = fila.querySelector('[data-estado-cell]');
                var def = CB_BADGES[estado];
                if (celda && def) {
                    celda.innerHTML = '<span class="badge ' + def.clase + '">' + def.texto + '</span>';
                }
            });
        })
        .catch(function () { /* silencioso */ });
}

// ---- Monitoreo de estudiantes: listas de activos y vencidos ----
var ultimoMonitoreoActivos = null;
var ultimoMonitoreoVencidos = null;

function pollMonitoreo() {
    craiObtener('/prestamos/api/monitoreo/')
        .then(function (data) {
            // No pisar la vista mientras el usuario está filtrando.
            var buscador = document.getElementById('buscarMonitoreo');
            if (buscador && buscador.value.trim() !== '') { return; }

            var activos = document.getElementById('monitoreoActivosLista');
            if (activos && data.activos_html && data.activos_html !== ultimoMonitoreoActivos) {
                activos.innerHTML = data.activos_html;
                ultimoMonitoreoActivos = data.activos_html;
            }
            var vencidos = document.getElementById('monitoreoVencidosLista');
            if (vencidos && data.vencidos_html && data.vencidos_html !== ultimoMonitoreoVencidos) {
                vencidos.innerHTML = data.vencidos_html;
                ultimoMonitoreoVencidos = data.vencidos_html;
            }
            var cActivos = document.getElementById('monitoreoCountActivos');
            if (cActivos) { cActivos.textContent = data.count_activos; }
            var cVencidos = document.getElementById('monitoreoCountVencidos');
            if (cVencidos) { cVencidos.textContent = data.count_vencidos; }
        })
        .catch(function () { /* silencioso */ });
}

document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('tbodyUltimosPrestamos')) {
        setInterval(pollDashboard, REALTIME_DASHBOARD);
    }
    if (document.getElementById('listaPrestamosHoy')) {
        setInterval(pollPrestamosHoy, REALTIME_INTERVALO);
    }
    if (document.querySelector('[data-estado-cell]')) {
        setInterval(pollChromebooks, REALTIME_INTERVALO);
    }
    if (document.getElementById('monitoreoActivosLista')) {
        setInterval(pollMonitoreo, REALTIME_INTERVALO);
    }
});
