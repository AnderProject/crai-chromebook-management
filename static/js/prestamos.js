var chromebookSeleccionado = null;
var estudianteSeleccionado = null;

var horaInicioEditada = false;

document.addEventListener('DOMContentLoaded', function() {

    // Resumen de horario en vivo
    ['fechaPrestamo', 'horaInicio', 'horaFin'].forEach(function(idCampo) {
        var el = document.getElementById(idCampo);
        if (el) { el.addEventListener('change', actualizarInfoHorario); }
    });

    // Hora de inicio = hora actual, en vivo (hasta que el usuario la edite manualmente)
    var campoHoraInicio = document.getElementById('horaInicio');
    if (campoHoraInicio) {
        campoHoraInicio.addEventListener('input', dejarDeSeguirHora);
        sincronizarHoraInicio();
        setInterval(sincronizarHoraInicio, 15000);
    }

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

        var modal = new bootstrap.Modal(document.getElementById('modalConfirmarPrestamo'));
        modal.show();

        var btnFinal = document.getElementById('btnConfirmarPrestamoFinal');
        btnFinal.onclick = function () {
            ejecutarRegistroPrestamo(modal, btnFinal, fecha, horaInicio, horaFin);
        };
    });

});

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
            hora_fin: horaFin
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
    actualizarInfoHorario();
}

function dejarDeSeguirHora() {
    horaInicioEditada = true;
    var chip = document.getElementById('horaInicioVivo');
    if (chip) { chip.style.display = 'none'; }
}

function sincronizarHoraInicio() {
    if (horaInicioEditada) { return; }
    var campo = document.getElementById('horaInicio');
    if (!campo) { return; }
    var ahora = new Date();
    var hh = String(ahora.getHours()).padStart(2, '0');
    var mm = String(ahora.getMinutes()).padStart(2, '0');
    var nueva = hh + ':' + mm;
    if (campo.value !== nueva) {
        campo.value = nueva;
        actualizarInfoHorario();
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