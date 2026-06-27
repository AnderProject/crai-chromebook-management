// =============================================
// RESERVACIONES PENDIENTES - REVELAR CÓDIGO INLINE
// El código queda oculto (••••••) y se revela en el mismo espacio
// escribiendo la cédula del estudiante, sin abrir modales.
// =============================================

// Activa el modo "ingresar cédula" dentro de la misma celda del código.
function activarRevelarInline(reservaId) {
    var celda = document.getElementById('codigo-reserva-' + reservaId);
    if (!celda || celda.querySelector('.cedula-inline')) { return; }

    celda.innerHTML =
        '<div class="revelar-inline">' +
        '  <input type="text" class="cedula-inline" placeholder="Cédula" inputmode="numeric" autocomplete="off" maxlength="10">' +
        '  <button type="button" class="btn-inline btn-inline-ok" title="Revelar"><i class="bi bi-check-lg"></i></button>' +
        '  <button type="button" class="btn-inline btn-inline-cancel" title="Cancelar"><i class="bi bi-x-lg"></i></button>' +
        '</div>';

    var input = celda.querySelector('.cedula-inline');
    var ok = celda.querySelector('.btn-inline-ok');
    var cancel = celda.querySelector('.btn-inline-cancel');

    input.focus();
    ok.addEventListener('click', function () { enviarRevelarInline(reservaId, input); });
    cancel.addEventListener('click', function () { restaurarOculto(reservaId); });
    input.addEventListener('keyup', function (e) {
        if (e.key === 'Enter') { enviarRevelarInline(reservaId, input); }
        if (e.key === 'Escape') { restaurarOculto(reservaId); }
    });
}

function enviarRevelarInline(reservaId, input) {
    var cedula = input.value.trim();
    if (!cedula) { marcarErrorInline(input); return; }

    fetch('/prestamos/api/revelar-codigo-reserva/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ reserva_id: reservaId, cedula: cedula })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (data.success) {
            mostrarCodigoRevelado(reservaId, data.codigo);
        } else {
            marcarErrorInline(input, data.message);
        }
    })
    .catch(function () { marcarErrorInline(input, 'Error de conexión'); });
}

function marcarErrorInline(input, mensaje) {
    input.classList.remove('cedula-error');
    // reinicia la animación de shake
    void input.offsetWidth;
    input.classList.add('cedula-error');
    if (mensaje) { input.title = mensaje; input.placeholder = mensaje; }
}

function mostrarCodigoRevelado(reservaId, codigo) {
    var celda = document.getElementById('codigo-reserva-' + reservaId);
    if (!celda) { return; }
    celda.innerHTML =
        '<span class="codigo-reserva codigo-revelado codigo-accionable" role="button" tabindex="0" ' +
        'title="Clic para confirmar la reserva con evidencia">' + codigo +
        '<i class="bi bi-camera-fill codigo-accion-icono"></i></span>' +
        '<button type="button" class="btn-revelar" title="Ocultar código"><i class="bi bi-eye-slash"></i></button>';

    // Al hacer clic (o Enter) sobre el código revelado se inicia la confirmación
    // de la reserva: valida y abre el modal de evidencia QR (verificar_reservacion.js).
    var span = celda.querySelector('.codigo-revelado');
    span.addEventListener('click', function () { iniciarReservaDesdeCodigo(codigo); });
    span.addEventListener('keyup', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { iniciarReservaDesdeCodigo(codigo); }
    });
    celda.querySelector('.btn-revelar').addEventListener('click', function () { restaurarOculto(reservaId); });
}

function restaurarOculto(reservaId) {
    var celda = document.getElementById('codigo-reserva-' + reservaId);
    if (!celda) { return; }
    celda.innerHTML =
        '<span class="codigo-reserva codigo-mask">••••••</span>' +
        '<button type="button" class="btn-revelar" title="Revelar con cédula" onclick="activarRevelarInline(' + reservaId + ')"><i class="bi bi-eye"></i></button>';
}

// =============================================
// BÚSQUEDA EN VIVO DE RESERVACIONES PENDIENTES
// Filtra las filas por estudiante, carrera, fecha u horario mientras se escribe.
// =============================================
document.addEventListener('DOMContentLoaded', function () {
    var input = document.getElementById('buscadorReservas');
    var tbody = document.getElementById('tbodyReservasPendientes');
    if (!input || !tbody) { return; }

    var badge = document.getElementById('badgeReservasPendientes');

    input.addEventListener('input', function () {
        var termino = input.value.trim().toLowerCase();
        // Solo filas reales (las que tienen reserva); ignora filas de aviso (colspan).
        var filas = tbody.querySelectorAll('tr');
        var visibles = 0;

        filas.forEach(function (fila) {
            if (fila.id === 'filaSinResultados' || fila.querySelector('td[colspan]')) { return; }
            var texto = fila.textContent.toLowerCase();
            var coincide = texto.indexOf(termino) !== -1;
            fila.style.display = coincide ? '' : 'none';
            if (coincide) { visibles++; }
        });

        if (badge) { badge.textContent = visibles; }
        mostrarFilaSinResultados(tbody, termino !== '' && visibles === 0);
    });
});

// Inserta/quita una fila de "sin coincidencias" cuando la búsqueda no encuentra nada.
function mostrarFilaSinResultados(tbody, mostrar) {
    var fila = document.getElementById('filaSinResultados');
    if (mostrar && !fila) {
        fila = document.createElement('tr');
        fila.id = 'filaSinResultados';
        fila.innerHTML = '<td colspan="6" class="text-center text-muted py-4">' +
            '<i class="bi bi-search display-6 d-block mb-2"></i>Sin coincidencias para tu búsqueda</td>';
        tbody.appendChild(fila);
    } else if (!mostrar && fila) {
        fila.remove();
    }
}

// =============================================
// CANCELAR RESERVACIÓN PENDIENTE (desde el badge de estado)
// Al hacer clic en "Pendiente" se abre un modal que exige la cédula del
// personal logueado (admin/recepcionista) para confirmar la cancelación.
// =============================================
var _cancelarReservaId = null;

function abrirCancelarReserva(reservaId, nombre) {
    _cancelarReservaId = reservaId;

    var lbl = document.getElementById('cancelarNombre');
    if (lbl) { lbl.textContent = nombre || 'este estudiante'; }

    var input = document.getElementById('cancelarCedula');
    var err = document.getElementById('cancelarError');
    if (input) { input.value = ''; input.classList.remove('cedula-error'); }
    if (err) { err.textContent = ''; }

    var modalEl = document.getElementById('modalCancelarReserva');
    if (modalEl && window.bootstrap) {
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
        setTimeout(function () { if (input) { input.focus(); } }, 300);
    }
}

function enviarCancelarReserva() {
    var input = document.getElementById('cancelarCedula');
    var err = document.getElementById('cancelarError');
    var btn = document.getElementById('btnCancelarReserva');
    if (!input || _cancelarReservaId == null) { return; }

    var cedula = input.value.trim();
    if (!cedula) {
        input.classList.add('cedula-error');
        if (err) { err.textContent = 'Ingresa tu cédula para confirmar.'; }
        return;
    }

    if (btn) { btn.disabled = true; }
    fetch('/prestamos/api/cancelar-reserva/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ reserva_id: _cancelarReservaId, cedula: cedula })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (btn) { btn.disabled = false; }
        if (data.success) {
            var modalEl = document.getElementById('modalCancelarReserva');
            if (modalEl && window.bootstrap) { bootstrap.Modal.getOrCreateInstance(modalEl).hide(); }
            quitarFilaReserva(_cancelarReservaId);
            _cancelarReservaId = null;
            if (window.mostrarToast) { mostrarToast('Reservación cancelada', 'success'); }
        } else {
            input.classList.remove('cedula-error');
            void input.offsetWidth; // reinicia la animación de shake
            input.classList.add('cedula-error');
            if (err) { err.textContent = data.message || 'No se pudo cancelar.'; }
        }
    })
    .catch(function () {
        if (btn) { btn.disabled = false; }
        if (err) { err.textContent = 'Error de conexión.'; }
    });
}

// Quita la fila de la reserva cancelada y actualiza el contador del encabezado.
function quitarFilaReserva(reservaId) {
    var celda = document.getElementById('codigo-reserva-' + reservaId);
    var fila = celda ? celda.closest('tr') : null;
    if (fila) { fila.remove(); }

    var badge = document.getElementById('badgeReservasPendientes');
    if (badge) {
        var n = parseInt(badge.textContent, 10);
        if (!isNaN(n) && n > 0) { badge.textContent = n - 1; }
    }

    var tbody = document.getElementById('tbodyReservasPendientes');
    if (tbody) {
        var quedan = false;
        tbody.querySelectorAll('tr').forEach(function (tr) {
            if (!tr.querySelector('td[colspan]')) { quedan = true; }
        });
        if (!quedan && !tbody.querySelector('.reservas-vacio')) {
            var vacio = document.createElement('tr');
            vacio.className = 'reservas-vacio';
            vacio.innerHTML = '<td colspan="6" class="text-center text-muted py-3">' +
                '<i class="bi bi-calendar-x fs-3 d-block mb-1"></i>No hay reservaciones pendientes</td>';
            tbody.appendChild(vacio);
        }
    }
}

document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('btnCancelarReserva');
    if (btn) { btn.addEventListener('click', enviarCancelarReserva); }

    var input = document.getElementById('cancelarCedula');
    if (input) {
        input.addEventListener('keyup', function (e) {
            if (e.key === 'Enter') { enviarCancelarReserva(); }
        });
    }
});
