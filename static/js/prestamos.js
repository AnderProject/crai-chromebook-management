var chromebookSeleccionado = null;
var estudianteSeleccionado = null;

document.addEventListener('DOMContentLoaded', function() {

    // Resumen de horario en vivo
    ['fechaPrestamo', 'horaInicio', 'horaFin'].forEach(function(idCampo) {
        var el = document.getElementById(idCampo);
        if (el) { el.addEventListener('change', actualizarInfoHorario); }
    });
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
                div.innerHTML = '<span class="text-success"><i class="bi bi-check-circle me-1"></i>' + data.data.codigo + ' • ' + data.data.marca + ' ' + data.data.modelo + ' • <strong>' + data.data.estado + '</strong></span>';
            } else {
                chromebookSeleccionado = null;
                div.innerHTML = '<span class="text-danger"><i class="bi bi-x-circle me-1"></i>' + data.message + '</span>';
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
                div.innerHTML = '<span class="text-info"><i class="bi bi-person-check me-1"></i>' + data.data.nombre + ' • ' + data.data.carrera + '</span>';
            } else {
                estudianteSeleccionado = null;
                div.innerHTML = '<span class="text-danger"><i class="bi bi-person-x me-1"></i>' + data.message + '</span>';
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

        var esReserva = new Date(fecha + 'T' + horaInicio) > new Date();
        var verbo = esReserva ? 'reservar' : 'prestar';
        if (!confirm('¿Confirmar ' + verbo + ' ' + chromebookSeleccionado.codigo + ' a ' + estudianteSeleccionado.nombre + ' el ' + fecha + ' de ' + horaInicio + ' a ' + horaFin + '?')) {
            return;
        }

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
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                mostrarToastTrasReload(data.message, 'success');
                location.reload();
            } else {
                mostrarToast(data.message, 'error');
            }
        });
    });

});

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

function getCSRFToken() {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.startsWith('csrftoken=')) return c.substring('csrftoken='.length);
    }
    return '';
}