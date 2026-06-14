document.addEventListener('DOMContentLoaded', function() {
    
    // Inicializar fecha hoy
    seleccionarFecha('hoy');
    
    // Radio buttons de duración
    var radios = document.querySelectorAll('.duracion-radio');
    radios.forEach(function(radio) {
        radio.addEventListener('change', function() {
            document.querySelectorAll('.duracion-card').forEach(function(card) {
                card.style.borderColor = '#eef0f5';
                card.style.background = '#f8f9fb';
            });
            var card = this.nextElementSibling;
            card.style.borderColor = '#1a237e';
            card.style.background = '#eef1ff';
        });
    });
    
    // Mover barra de pasos al hacer clic en los campos
    document.getElementById('fechaManual').addEventListener('focus', function() {
        activarPaso(1);
    });
    
    document.querySelectorAll('.btn-hora').forEach(function(btn) {
        btn.addEventListener('click', function() {
            activarPaso(2);
        });
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
// HORA
// =============================================
function seleccionarHora(hora) {
    document.querySelectorAll('.btn-hora').forEach(function(b) {
        b.classList.remove('activo');
    });
    event.target.classList.add('activo');
    document.getElementById('horaSeleccionada').value = hora;
    activarPaso(2);
}

// =============================================
// ENVIAR RESERVA
// =============================================
function enviarReserva(event) {
    event.preventDefault();
    
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
            document.getElementById('confirmacionReserva').style.display = 'block';
            document.getElementById('codigoConfirmacion').textContent = data.codigo;
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