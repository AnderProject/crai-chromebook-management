// =============================================
// ACTUALIZACIÓN EN VIVO (ADMIN) - CRAI UNEMI
// Polling ligero por sección. Se auto-inicia según las anclas presentes en el DOM.
// =============================================

var REALTIME_INTERVALO = 20000; // 20s

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

// ---- Dashboard: contadores + tabla últimos préstamos ----
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

document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('tbodyUltimosPrestamos')) {
        setInterval(pollDashboard, REALTIME_INTERVALO);
    }
    if (document.getElementById('listaPrestamosHoy')) {
        setInterval(pollPrestamosHoy, REALTIME_INTERVALO);
    }
    if (document.querySelector('[data-estado-cell]')) {
        setInterval(pollChromebooks, REALTIME_INTERVALO);
    }
});
