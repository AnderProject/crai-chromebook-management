// =============================================
// DEVOLUCIÓN DE PRÉSTAMO CON EVIDENCIA - CRAI UNEMI
// =============================================

var prestamoADevolver = null;
var devFotoNombre = null;
var devToken = null;
var devIntervaloVerif = null;
var devIntervaloQR = null;
var devTiempo = 45;

// Abre el modal de evidencia (QR) antes de devolver el equipo.
function confirmarDevolucion(prestamoId, codigo) {
    prestamoADevolver = prestamoId;
    devFotoNombre = null;

    // Reset visual del modal.
    document.getElementById('devEquipoTexto').textContent = 'Equipo ' + codigo + ' · toma una foto antes de devolverlo';
    document.getElementById('qrContainerDev').style.display = 'inline-block';
    document.getElementById('vistaPreviaContainerDev').style.display = 'none';
    document.getElementById('qrImagenDev').style.opacity = '1';
    document.getElementById('btnConfirmarDev').disabled = true;

    generarQRDevolucion();

    var modal = new bootstrap.Modal(document.getElementById('modalQREvidenciaDev'));
    modal.show();

    document.getElementById('modalQREvidenciaDev').addEventListener('hidden.bs.modal', function() {
        clearInterval(devIntervaloVerif);
        clearInterval(devIntervaloQR);
    }, { once: true });
}

function generarQRDevolucion() {
    devTiempo = 45;
    devFotoNombre = null;
    document.getElementById('btnConfirmarDev').disabled = true;
    document.getElementById('estadoEvidenciaDev').innerHTML =
        '<span class="text-warning"><i class="bi bi-hourglass-split"></i> Esperando foto... (' + devTiempo + 's)</span>';

    if (devIntervaloVerif) clearInterval(devIntervaloVerif);
    if (devIntervaloQR) clearInterval(devIntervaloQR);

    fetch('/prestamos/api/generar-qr-evidencia/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ prestamo_id: prestamoADevolver, tipo: 'devolucion' })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            devToken = data.token;
            document.getElementById('qrImagenDev').src =
                'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + encodeURIComponent(data.url);
            devIntervaloVerif = setInterval(verificarEvidenciaDev, 3000);
            devIntervaloQR = setInterval(contadorQRDev, 1000);
        }
    });
}

function contadorQRDev() {
    devTiempo--;
    if (devTiempo <= 0) {
        clearInterval(devIntervaloQR);
        document.getElementById('estadoEvidenciaDev').innerHTML =
            '<span class="text-info"><i class="bi bi-arrow-repeat"></i> Generando nuevo QR...</span>';
        document.getElementById('qrImagenDev').style.opacity = '0.5';
        setTimeout(function() {
            document.getElementById('qrImagenDev').style.opacity = '1';
            generarQRDevolucion();
        }, 1000);
    } else {
        document.getElementById('estadoEvidenciaDev').innerHTML =
            '<span class="text-warning"><i class="bi bi-hourglass-split"></i> Esperando foto... (' + devTiempo + 's)</span>';
    }
}

function verificarEvidenciaDev() {
    if (!devToken) return;

    fetch('/prestamos/api/verificar-evidencia/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ token: devToken })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.recibida) {
            clearInterval(devIntervaloVerif);
            clearInterval(devIntervaloQR);

            devFotoNombre = data.nombre_archivo || '';
            document.getElementById('btnConfirmarDev').disabled = false;
            document.getElementById('estadoEvidenciaDev').innerHTML =
                '<span class="text-success"><i class="bi bi-check-circle"></i> ¡Foto recibida! Confirma la devolución.</span>';
            document.getElementById('qrContainerDev').style.display = 'none';
            document.getElementById('vistaPreviaContainerDev').style.display = 'block';
        }
    });
}

// Devuelve con la foto tomada.
function confirmarDevolucionFinal() {
    ejecutarDevolucion(devFotoNombre || '');
}

// Devuelve sin foto (cuando la cámara no está disponible).
function devolverSinEvidencia() {
    ejecutarDevolucion('');
}

function ejecutarDevolucion(fotoNombre) {
    if (!prestamoADevolver) return;

    clearInterval(devIntervaloVerif);
    clearInterval(devIntervaloQR);

    var modalQR = bootstrap.Modal.getInstance(document.getElementById('modalQREvidenciaDev'));
    if (modalQR) modalQR.hide();

    fetch('/prestamos/api/devolver-prestamo/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ prestamo_id: prestamoADevolver, foto_nombre: fotoNombre })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        var icono = document.getElementById('devolucionIcono');
        var titulo = document.getElementById('devolucionTitulo');
        var texto = document.getElementById('devolucionTexto');

        if (data.success) {
            icono.innerHTML = '<i class="bi bi-check-circle-fill text-success" style="font-size: 3rem;"></i>';
            titulo.textContent = '¡Devuelto!';
            texto.textContent = data.message;
        } else {
            icono.innerHTML = '<i class="bi bi-x-circle-fill text-danger" style="font-size: 3rem;"></i>';
            titulo.textContent = 'Error';
            texto.textContent = data.message;
        }

        var modalMensaje = new bootstrap.Modal(document.getElementById('modalMensajeDevolucion'));
        modalMensaje.show();
        prestamoADevolver = null;
        devFotoNombre = null;
    });
}

function getCSRFToken() {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.startsWith('csrftoken=')) return c.substring('csrftoken='.length);
    }
    return '';
}

// =============================================
// TIEMPO RESTANTE EN TIEMPO REAL
// =============================================
function actualizarTiemposRestantes() {
    document.querySelectorAll('.tiempo-restante').forEach(function(el) {
        var fechaDevolucion = new Date(el.getAttribute('data-devolucion'));
        var ahora = new Date();
        var diferencia = fechaDevolucion - ahora;

        if (diferencia <= 0) {
            el.innerHTML = '<span style="color: #dc3545; font-weight: 700;">⚠️ VENCIDO</span>';
            el.style.animation = 'alertaVencido 1s infinite';
        } else {
            var horas = Math.floor(diferencia / (1000 * 60 * 60));
            var minutos = Math.floor((diferencia % (1000 * 60 * 60)) / (1000 * 60));

            if (horas < 1) {
                el.innerHTML = '<span style="color: #dc3545; font-weight: 700;">⏰ ' + minutos + 'min restantes</span>';
            } else if (horas < 2) {
                el.innerHTML = '<span style="color: #dc3545; font-weight: 700;">⏰ ' + horas + 'h ' + minutos + 'min</span>';
            } else if (horas < 4) {
                el.innerHTML = '<span style="color: #ff9800; font-weight: 600;">🟡 ' + horas + 'h ' + minutos + 'min</span>';
            } else {
                el.innerHTML = '<span style="color: #28a745;">🟢 ' + horas + 'h ' + minutos + 'min</span>';
            }
        }
    });
}

// Actualizar cada 30 segundos
setInterval(actualizarTiemposRestantes, 30000);

// Ejecutar al cargar
document.addEventListener('DOMContentLoaded', function() {
    actualizarTiemposRestantes();
});
