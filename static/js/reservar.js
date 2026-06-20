document.addEventListener('DOMContentLoaded', function() {

    // Inicializar fecha hoy
    seleccionarFecha('hoy');

    // Mover barra de pasos al interactuar con los campos
    document.getElementById('fechaManual').addEventListener('focus', function() {
        activarPaso(1);
    });

    document.querySelector('textarea[name="motivo"]').addEventListener('focus', function() {
        activarPaso(3);
    });

});

// =============================================
// BARRA DE PASOS
// =============================================
function activarPaso(numero) {
    var pasos = document.querySelectorAll('.paso');
    pasos.forEach(function(paso, index) {
        paso.classList.remove('activo');
        if (index < numero) {
            paso.classList.add('activo');
        }
    });
}

// =============================================
// FECHA
// =============================================
function seleccionarFecha(tipo) {
    var hoy = new Date();
    var fecha;

    if (tipo === 'hoy') {
        fecha = hoy;
    } else if (tipo === 'manana') {
        fecha = new Date(hoy);
        fecha.setDate(fecha.getDate() + 1);
    }

    var fechaStr = fecha.toISOString().split('T')[0];
    document.getElementById('fechaSeleccionada').value = fechaStr;
    document.getElementById('fechaManual').value = fechaStr;

    document.querySelectorAll('.btn-fecha').forEach(function(b) {
        b.classList.remove('activo');
    });

    if (event && event.target) {
        event.target.classList.add('activo');
    } else {
        document.querySelector('.btn-fecha').classList.add('activo');
    }

    activarPaso(1);
}

function fechaManualSeleccionada() {
    var fecha = document.getElementById('fechaManual').value;
    document.getElementById('fechaSeleccionada').value = fecha;
    document.querySelectorAll('.btn-fecha').forEach(function(b) {
        b.classList.remove('activo');
    });
    activarPaso(1);
}

// =============================================
// ENVIAR RESERVA
// =============================================
function enviarReserva(event) {
    event.preventDefault();

    // Validar que la hora de fin sea mayor que la de inicio
    var inicio = document.getElementById('horaInicio').value;
    var fin = document.getElementById('horaFin').value;
    if (!inicio || !fin) {
        alert('Selecciona la hora de inicio y la hora de fin.');
        return;
    }
    if (fin <= inicio) {
        alert('La hora de fin debe ser mayor que la hora de inicio.');
        return;
    }

    activarPaso(3);

    var form = document.getElementById('formReserva');
    var data = new FormData(form);

    form.style.display = 'none';
    document.getElementById('loaderReserva').style.display = 'block';

    fetch('/estudiantes/reservar/', {
        method: 'POST',
        body: data,
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        setTimeout(function() {
            document.getElementById('loaderReserva').style.display = 'none';
            if (data.success) {
                document.getElementById('confirmacionReserva').style.display = 'block';
                document.getElementById('codigoConfirmacion').textContent = data.codigo;
            } else {
                form.style.display = 'block';
                alert(data.message || 'No se pudo crear la reserva.');
            }
        }, 1500);
    })
    .catch(function() {
        document.getElementById('loaderReserva').style.display = 'none';
        form.style.display = 'block';
        alert('Error al enviar la reserva.');
    });
}

function nuevaReserva() {
    document.getElementById('confirmacionReserva').style.display = 'none';
    document.getElementById('formReserva').style.display = 'block';
    document.getElementById('formReserva').reset();
    seleccionarFecha('hoy');
    activarPaso(1);
}

function getCookie(name) {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.startsWith(name + '=')) return c.substring(name.length + 1);
    }
    return '';
}
