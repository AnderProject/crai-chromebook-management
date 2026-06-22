var chromebookSeleccionado = null;
var estudianteSeleccionado = null;

var horaInicioEditada = false;

// Captura de foto de entrega (préstamo inmediato)
var entregaFotoNombre = null;   // nombre del archivo subido al servidor
var entregaTempKey = null;      // clave temporal para nombrar la foto antes de tener Prestamo
var entregaStream = null;       // stream activo de la webcam

document.addEventListener('DOMContentLoaded', function() {

    // Resumen de horario en vivo: reacciona a los cambios de los selectores de hora.
    if (window.CraiTP) {
        CraiTP.onChange('horaInicio', function (e) {
            if (e.detail.byUser) { dejarDeSeguirHora(); }
            actualizarInfoHorario();
        });
        CraiTP.onChange('horaFin', actualizarInfoHorario);
    }

    // Hora de inicio = hora actual, en vivo (hasta que el usuario la edite manualmente)
    sincronizarHoraInicio();
    setInterval(sincronizarHoraInicio, 15000);

    actualizarInfoHorario();

    // Buscar Chromebook
    document.getElementById('btnBuscarChromebook').addEventListener('click', function() {
        var codigo = document.getElementById('codigoChromebook').value.trim();
        if (!codigo) return;
        
        fetch('/prestamos/api/buscar-chromebook/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify({ codigo: codigo })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var div = document.getElementById('infoChromebook');
            if (data.success) {
                chromebookSeleccionado = data.data;
                div.innerHTML = tarjetaResultado('ok', 'bi-laptop', data.data.codigo,
                    data.data.marca + ' ' + data.data.modelo,
                    '<span class="resultado-estado estado-' + data.data.estado + '">' + data.data.estado + '</span>');
            } else {
                chromebookSeleccionado = null;
                div.innerHTML = tarjetaResultado('error', 'bi-x-circle', 'No encontrado', data.message, '');
            }
        });
    });
    
    // Buscar Estudiante
    document.getElementById('btnBuscarEstudiante').addEventListener('click', function() {
        var cedula = document.getElementById('cedulaEstudiante').value.trim();
        if (!cedula) return;
        
        fetch('/prestamos/api/buscar-estudiante/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify({ cedula: cedula })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var div = document.getElementById('infoEstudiante');
            if (data.success) {
                estudianteSeleccionado = data.data;
                div.innerHTML = tarjetaResultado('ok', 'bi-person-check', data.data.nombre, data.data.carrera, '');
            } else {
                estudianteSeleccionado = null;
                div.innerHTML = tarjetaResultado('error', 'bi-person-x', 'No encontrado', data.message, '');
            }
        });
    });
    
    // Registrar préstamo / reserva
    document.getElementById('btnPrestarAhora').addEventListener('click', function() {
        if (!chromebookSeleccionado) { mostrarToast('Busca un Chromebook primero.', 'warning'); return; }
        if (!estudianteSeleccionado) { mostrarToast('Busca un estudiante primero.', 'warning'); return; }

        var fecha = document.getElementById('fechaPrestamo').value;
        var horaInicio = document.getElementById('horaInicio').value;
        var horaFin = document.getElementById('horaFin').value;

        if (!fecha || !horaInicio || !horaFin) {
            mostrarToast('Indica fecha, hora de inicio y hora de fin.', 'warning');
            return;
        }
        if (horaFin <= horaInicio) {
            mostrarToast('La hora de fin debe ser posterior a la de inicio.', 'warning');
            return;
        }
        if (horaInicio < '08:00' || horaFin > '17:00') {
            mostrarToast('El horario de atención del CRAI es de 08:00 a 17:00.', 'warning');
            return;
        }

        var esReserva = new Date(fecha + 'T' + horaInicio) > new Date();

        // Llenar y mostrar el modal de confirmación (en vez del confirm() del navegador)
        document.getElementById('confirmTitulo').textContent = esReserva ? 'Confirmar reserva' : 'Confirmar préstamo';
        document.getElementById('confirmSubtitulo').textContent = esReserva
            ? 'Se apartará el equipo para el horario indicado.'
            : 'Se entregará el equipo ahora mismo.';
        document.getElementById('confirmChromebook').textContent =
            chromebookSeleccionado.codigo + ' · ' + chromebookSeleccionado.marca + ' ' + chromebookSeleccionado.modelo;
        document.getElementById('confirmEstudiante').textContent = estudianteSeleccionado.nombre;
        document.getElementById('confirmFecha').textContent = fecha;
        document.getElementById('confirmHorario').textContent = horaInicio + ' – ' + horaFin;

        // La foto de entrega solo aplica al préstamo inmediato.
        prepararFotoEntrega(esReserva);

        var modal = new bootstrap.Modal(document.getElementById('modalConfirmarPrestamo'));
        modal.show();

        var btnFinal = document.getElementById('btnConfirmarPrestamoFinal');
        btnFinal.onclick = function () {
            ejecutarRegistroPrestamo(modal, btnFinal, fecha, horaInicio, horaFin);
        };
    });

    configurarFotoEntrega();

    // Detener la cámara si se cierra el modal de confirmación.
    var modalConfirm = document.getElementById('modalConfirmarPrestamo');
    if (modalConfirm) {
        modalConfirm.addEventListener('hidden.bs.modal', detenerCamaraEntrega);
    }

});

// =============================================
// FOTO DE ENTREGA (préstamo inmediato, opcional)
// =============================================
// Reinicia la sección de foto cada vez que se abre el modal.
function prepararFotoEntrega(esReserva) {
    entregaFotoNombre = null;
    entregaTempKey = null;
    detenerCamaraEntrega();

    var cont = document.getElementById('entregaFoto');
    if (!cont) { return; }
    cont.style.display = esReserva ? 'none' : 'block';

    document.getElementById('videoEntrega').style.display = 'none';
    document.getElementById('previewEntrega').style.display = 'none';
    document.getElementById('accionesCamaraEntrega').style.display = 'none';
    document.getElementById('accionesPreviewEntrega').style.display = 'none';
    document.getElementById('btnTomarFotoEntrega').style.display = 'inline-block';
}

function configurarFotoEntrega() {
    var btnTomar = document.getElementById('btnTomarFotoEntrega');
    if (!btnTomar) { return; }
    btnTomar.addEventListener('click', iniciarCamaraEntrega);
    document.getElementById('btnCapturarEntrega').addEventListener('click', capturarFotoEntrega);
    document.getElementById('btnCancelarCamaraEntrega').addEventListener('click', function () {
        detenerCamaraEntrega();
        document.getElementById('videoEntrega').style.display = 'none';
        document.getElementById('accionesCamaraEntrega').style.display = 'none';
        document.getElementById('btnTomarFotoEntrega').style.display = 'inline-block';
    });
    document.getElementById('btnRepetirFotoEntrega').addEventListener('click', function () {
        entregaFotoNombre = null;
        document.getElementById('previewEntrega').style.display = 'none';
        document.getElementById('accionesPreviewEntrega').style.display = 'none';
        iniciarCamaraEntrega();
    });
}

function iniciarCamaraEntrega() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        mostrarToast('Este dispositivo no permite acceder a la cámara.', 'warning');
        return;
    }
    var video = document.getElementById('videoEntrega');
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(function (stream) {
            entregaStream = stream;
            video.srcObject = stream;
            video.play();
            video.style.display = 'block';
            document.getElementById('previewEntrega').style.display = 'none';
            document.getElementById('accionesPreviewEntrega').style.display = 'none';
            document.getElementById('accionesCamaraEntrega').style.display = 'flex';
            document.getElementById('btnTomarFotoEntrega').style.display = 'none';
        })
        .catch(function () {
            mostrarToast('No se pudo acceder a la cámara.', 'error');
        });
}

function detenerCamaraEntrega() {
    if (entregaStream) {
        entregaStream.getTracks().forEach(function (t) { t.stop(); });
        entregaStream = null;
    }
}

function capturarFotoEntrega() {
    var video = document.getElementById('videoEntrega');
    var canvas = document.getElementById('canvasEntrega');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    var dataUrl = canvas.toDataURL('image/jpeg', 0.9);

    detenerCamaraEntrega();
    video.style.display = 'none';
    document.getElementById('accionesCamaraEntrega').style.display = 'none';

    var preview = document.getElementById('previewEntrega');
    preview.src = dataUrl;
    preview.style.display = 'block';
    document.getElementById('accionesPreviewEntrega').style.display = 'flex';

    subirFotoEntrega(dataUrl);
}

// Sube la foto al servidor; queda como archivo temporal hasta confirmar el préstamo.
function subirFotoEntrega(dataUrl) {
    if (!entregaTempKey) {
        entregaTempKey = 'ent' + (chromebookSeleccionado ? chromebookSeleccionado.id : '0') +
            '_' + (estudianteSeleccionado ? estudianteSeleccionado.user_id : '0') +
            '_' + (Date.now ? Date.now() : '');
    }
    fetch('/prestamos/api/subir-evidencia-webcam/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ temp_key: entregaTempKey, imagen: dataUrl })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (data.success) {
            entregaFotoNombre = data.nombre_archivo;
        } else {
            entregaFotoNombre = null;
            mostrarToast(data.message || 'No se pudo guardar la foto.', 'warning');
        }
    })
    .catch(function () {
        entregaFotoNombre = null;
        mostrarToast('Error al subir la foto.', 'error');
    });
}

function ejecutarRegistroPrestamo(modal, btnFinal, fecha, horaInicio, horaFin) {
    // Estado de carga en el botón del modal
    btnFinal.disabled = true;
    var htmlOriginal = btnFinal.innerHTML;
    btnFinal.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Procesando...';

    fetch('/prestamos/api/registrar-prestamo/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({
            chromebook_id: chromebookSeleccionado.id,
            user_id: estudianteSeleccionado.user_id,
            fecha: fecha,
            hora_inicio: horaInicio,
            hora_fin: horaFin,
            foto_nombre: entregaFotoNombre || ''
        })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (data.success) {
            mostrarToastTrasReload(data.message, 'success');
            location.reload();
        } else {
            btnFinal.disabled = false;
            btnFinal.innerHTML = htmlOriginal;
            modal.hide();
            mostrarToast(data.message, 'error');
        }
    })
    .catch(function () {
        btnFinal.disabled = false;
        btnFinal.innerHTML = htmlOriginal;
        modal.hide();
        mostrarToast('Error al conectar con el servidor.', 'error');
    });
}

function actualizarInfoHorario() {
    var info = document.getElementById('infoHorario');
    if (!info) { return; }
    var fecha = document.getElementById('fechaPrestamo').value;
    var horaInicio = document.getElementById('horaInicio').value;
    var horaFin = document.getElementById('horaFin').value;
    if (!fecha || !horaInicio || !horaFin) { info.textContent = ''; return; }

    var inicio = new Date(fecha + 'T' + horaInicio);
    var fin = new Date(fecha + 'T' + horaFin);
    if (fin <= inicio) {
        info.innerHTML = '<span class="text-danger"><i class="bi bi-exclamation-triangle me-1"></i>La hora de fin debe ser posterior.</span>';
        return;
    }
    var horas = Math.round((fin - inicio) / 3600000 * 10) / 10;
    var esReserva = inicio > new Date();
    var etiqueta = esReserva
        ? '<span class="text-primary"><i class="bi bi-calendar-check me-1"></i>Reserva</span>'
        : '<span class="text-success"><i class="bi bi-clock me-1"></i>Inmediato</span>';
    info.innerHTML = etiqueta + ' &bull; duración ' + horas + ' h';
}

function seleccionarFechaPrestamo(btn) {
    document.querySelectorAll('.btn-fecha-opt').forEach(function (b) { b.classList.remove('activo'); });
    btn.classList.add('activo');
    document.getElementById('fechaPrestamo').value = btn.dataset.fecha;
    actualizarBadgeDisponibles(btn.dataset.fecha);
    actualizarInfoHorario();
}

// Muestra en el badge la disponibilidad de la fecha elegida (hoy/mañana).
function actualizarBadgeDisponibles(fecha) {
    var badge = document.getElementById('badgeDisponibles');
    var num = document.getElementById('badgeDisponiblesNum');
    if (!badge || !num) { return; }
    var btnHoy = document.querySelector('.btn-fecha-opt');
    var esHoy = btnHoy && fecha === btnHoy.dataset.fecha;
    var n = esHoy ? parseInt(badge.dataset.dispHoy, 10) : parseInt(badge.dataset.dispManana, 10);
    if (isNaN(n)) { n = 0; }
    num.textContent = n;
}

function dejarDeSeguirHora() {
    horaInicioEditada = true;
    var chip = document.getElementById('horaInicioVivo');
    if (chip) { chip.style.display = 'none'; }
    // El usuario toma el control: ya no mostramos la opción "Ahora".
    if (window.CraiTP) { CraiTP.clearAhora('horaInicio'); }
}

function sincronizarHoraInicio() {
    if (horaInicioEditada || !window.CraiTP) { return; }
    var ahora = new Date();
    var nowMin = ahora.getHours() * 60 + ahora.getMinutes();
    if (nowMin < 8 * 60 || nowMin >= 17 * 60) {
        // Fuera del horario de atención (08:00–17:00): no seguir la hora actual.
        CraiTP.clearAhora('horaInicio');
        return;
    }
    var hh = String(ahora.getHours()).padStart(2, '0');
    var mm = String(ahora.getMinutes()).padStart(2, '0');
    var nueva = hh + ':' + mm;
    if (CraiTP.get('horaInicio') !== nueva) {
        CraiTP.setAhora('horaInicio', nueva);
        CraiTP.set('horaInicio', nueva, false);
    }
}

function tarjetaResultado(tipo, icono, titulo, detalle, extra) {
    return '<div class="resultado-card resultado-' + tipo + '">' +
        '<span class="resultado-icono"><i class="bi ' + icono + '"></i></span>' +
        '<span class="resultado-info"><strong>' + titulo + '</strong>' +
        '<span>' + detalle + '</span></span>' + (extra || '') + '</div>';
}

function getCSRFToken() {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.startsWith('csrftoken=')) return c.substring('csrftoken='.length);
    }
    return '';
}