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
        '<span class="codigo-reserva codigo-revelado">' + codigo + '</span>' +
        '<button type="button" class="btn-revelar" title="Ocultar código"><i class="bi bi-eye-slash"></i></button>';
    celda.querySelector('.btn-revelar').addEventListener('click', function () { restaurarOculto(reservaId); });
}

function restaurarOculto(reservaId) {
    var celda = document.getElementById('codigo-reserva-' + reservaId);
    if (!celda) { return; }
    celda.innerHTML =
        '<span class="codigo-reserva codigo-mask">••••••</span>' +
        '<button type="button" class="btn-revelar" title="Revelar con cédula" onclick="activarRevelarInline(' + reservaId + ')"><i class="bi bi-eye"></i></button>';
}
