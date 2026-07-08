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
    // Arranca en la opción QR (por defecto).
    mostrarOpcionQRDev();

    generarQRDevolucion();

    var modal = new bootstrap.Modal(document.getElementById('modalQREvidenciaDev'));
    modal.show();

    document.getElementById('modalQREvidenciaDev').addEventListener('hidden.bs.modal', function() {
        clearInterval(devIntervaloVerif);
        clearInterval(devIntervaloQR);
        detenerWebcamDev();
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

// =============================================
// OPCIÓN CÁMARA WEB (devolución)
// =============================================
var devWebcamStream = null;

function mostrarOpcionQRDev() {
    document.getElementById('segQRDev').classList.add('activo');
    document.getElementById('segWebcamDev').classList.remove('activo');
    document.getElementById('vistaQRDev').style.display = 'block';
    document.getElementById('vistaWebcamDev').style.display = 'none';
    detenerWebcamDev();
}

function mostrarOpcionWebcamDev() {
    document.getElementById('segWebcamDev').classList.add('activo');
    document.getElementById('segQRDev').classList.remove('activo');
    document.getElementById('vistaQRDev').style.display = 'none';
    document.getElementById('vistaWebcamDev').style.display = 'block';
    // Al usar la cámara web dejamos de depender del QR.
    clearInterval(devIntervaloVerif);
    clearInterval(devIntervaloQR);

    var video = document.getElementById('webcamVideoDev');
    var err = document.getElementById('webcamErrorDev');
    err.textContent = '';
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        err.innerHTML = '<span class="text-danger">Este dispositivo no permite acceder a la cámara.</span>';
        return;
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(function (stream) {
            devWebcamStream = stream;
            video.srcObject = stream;
            video.play();
        })
        .catch(function () {
            err.innerHTML = '<span class="text-danger">No se pudo acceder a la cámara. Usa la opción del celular (QR).</span>';
        });
}

function detenerWebcamDev() {
    if (devWebcamStream) {
        devWebcamStream.getTracks().forEach(function (t) { t.stop(); });
        devWebcamStream = null;
    }
}

function capturarFotoWebcamDev() {
    var video = document.getElementById('webcamVideoDev');
    var canvas = document.getElementById('webcamCanvasDev');
    if (!video.videoWidth) {
        document.getElementById('webcamErrorDev').innerHTML = '<span class="text-warning">La cámara aún no está lista.</span>';
        return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    var dataUrl = canvas.toDataURL('image/jpeg', 0.9);
    detenerWebcamDev();

    document.getElementById('estadoEvidenciaDev').innerHTML =
        '<span class="text-info"><i class="bi bi-hourglass-split"></i> Subiendo foto...</span>';

    fetch('/prestamos/api/subir-evidencia-webcam/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ temp_key: 'dev' + prestamoADevolver + '_' + Date.now(), imagen: dataUrl })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (data.success) {
            devFotoNombre = data.nombre_archivo;
            document.getElementById('vistaWebcamDev').style.display = 'none';
            document.getElementById('vistaPreviaContainerDev').style.display = 'block';
            document.getElementById('btnConfirmarDev').disabled = false;
            document.getElementById('estadoEvidenciaDev').innerHTML =
                '<span class="text-success"><i class="bi bi-check-circle"></i> ¡Foto tomada! Confirma la devolución.</span>';
        } else {
            document.getElementById('webcamErrorDev').innerHTML =
                '<span class="text-danger">' + (data.message || 'No se pudo guardar la foto.') + '</span>';
        }
    })
    .catch(function () {
        document.getElementById('webcamErrorDev').innerHTML = '<span class="text-danger">Error al subir la foto.</span>';
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
