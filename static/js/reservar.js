// =============================================
// RESERVAR CHROMEBOOK - CRAI UNEMI
// =============================================

// Slots de 30 min dentro del horario permitido (08:00–17:00)
var HORA_MIN = 8 * 60;    // 08:00 en minutos
var HORA_MAX = 17 * 60;   // 17:00 en minutos

document.addEventListener('DOMContentLoaded', function () {

    // Espera a que los timepickers estén registrados antes de fijar la fecha/hora.
    // Si no, `setMin` no encuentra el selector y las horas ya pasadas quedarían
    // habilitadas (deben salir deshabilitadas cuando la fecha es hoy).
    esperarTimepicker(function () {
        // Al elegir una hora manualmente, avanza el indicador de pasos.
        // En cualquier cambio de hora, refresca el resumen en vivo.
        if (window.CraiTP) {
            CraiTP.onChange('horaInicio', function (e) { if (e.detail.byUser) { activarPaso(2); } actualizarResumen(); });
            CraiTP.onChange('horaFin', function (e) { if (e.detail.byUser) { activarPaso(2); } actualizarResumen(); });
        }
        seleccionarFecha('hoy');
    });

    var motivo = document.querySelector('textarea[name="motivo"]');
    if (motivo) motivo.addEventListener('focus', function () { activarPaso(3); });
});

// Ejecuta cb cuando los timepickers ya están inicializados (CraiTP con valor),
// sin importar el orden en que se ejecuten los scripts.
function esperarTimepicker(cb) {
    if (window.CraiTP && CraiTP.get('horaInicio')) { cb(); return; }
    var intentos = 0;
    var t = setInterval(function () {
        if ((window.CraiTP && CraiTP.get('horaInicio')) || ++intentos > 60) {
            clearInterval(t);
            cb();
        }
    }, 10);
}

// =============================================
// UTILIDADES DE TIEMPO
// =============================================
function pad(n) { return (n < 10 ? '0' : '') + n; }
function minutosAStr(min) { return pad(Math.floor(min / 60)) + ':' + pad(min % 60); }

// Fecha de mañana (YYYY-MM-DD) en zona horaria de Ecuador
function fechaManana() {
    var p = ahoraEcuador().fecha.split('-');
    var d = new Date(Date.UTC(+p[0], +p[1] - 1, +p[2]));
    d.setUTCDate(d.getUTCDate() + 1);
    return d.toISOString().split('T')[0];
}

// Fecha y hora actuales en zona horaria de Ecuador (independiente del equipo)
function ahoraEcuador() {
    var fmt = new Intl.DateTimeFormat('en-CA', {
        timeZone: 'America/Guayaquil',
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false
    });
    var parts = {};
    fmt.formatToParts(new Date()).forEach(function (p) { parts[p.type] = p.value; });
    return {
        fecha: parts.year + '-' + parts.month + '-' + parts.day,
        hora: parseInt(parts.hour, 10) % 24,
        min: parseInt(parts.minute, 10)
    };
}

// =============================================
// MODAL DE ALERTA (reemplaza al alert nativo)
// =============================================
function mostrarAlerta(mensaje) {
    var modal = document.getElementById('modalAlerta');
    if (!modal) { window.alert(mensaje); return; }
    document.getElementById('modalAlertaMsg').textContent = mensaje;
    modal.classList.add('visible');
}

function cerrarAlerta() {
    var modal = document.getElementById('modalAlerta');
    if (modal) modal.classList.remove('visible');
}

// =============================================
// BARRA DE PASOS
// =============================================
function activarPaso(numero) {
    document.querySelectorAll('.paso').forEach(function (paso, index) {
        paso.classList.remove('activo');
        if (index < numero) paso.classList.add('activo');
    });
}

// =============================================
// FECHA
// =============================================
function seleccionarFecha(tipo) {
    var ec = ahoraEcuador();
    var fecha = ec.fecha;

    if (tipo === 'manana') {
        var p = ec.fecha.split('-');
        var d = new Date(Date.UTC(+p[0], +p[1] - 1, +p[2]));
        d.setUTCDate(d.getUTCDate() + 1);
        fecha = d.toISOString().split('T')[0];
    }

    document.getElementById('fechaSeleccionada').value = fecha;

    document.querySelectorAll('.btn-fecha').forEach(function (b) { b.classList.remove('activo'); });
    if (typeof event !== 'undefined' && event && event.target && event.target.classList.contains('btn-fecha')) {
        event.target.classList.add('activo');
    } else {
        document.querySelector('.btn-fecha').classList.add('activo');
    }

    actualizarHorasPorFecha();
    actualizarDisponibilidad();
    actualizarResumen();
    activarPaso(1);
}

// =============================================
// RESUMEN EN VIVO (día · horario · duración)
// Se actualiza al cambiar la fecha o la hora.
// =============================================
function actualizarResumen() {
    var elDia = document.getElementById('resDia');
    if (!elDia) { return; }
    var elHorario = document.getElementById('resHorario');
    var elDur = document.getElementById('resDuracion');

    var fecha = document.getElementById('fechaSeleccionada').value;
    var inicio = document.getElementById('horaInicio').value;
    var fin = document.getElementById('horaFin').value;

    // Día (Hoy / Mañana + fecha corta)
    if (fecha) {
        var ec = ahoraEcuador();
        var etiqueta = (fecha === ec.fecha) ? 'Hoy' : (fecha === fechaManana() ? 'Mañana' : 'Fecha');
        var p = fecha.split('-');
        elDia.textContent = etiqueta + ' · ' + p[2] + '/' + p[1];
    } else {
        elDia.textContent = '—';
    }

    // Horario
    elHorario.textContent = (inicio && fin) ? (inicio + ' – ' + fin) : '—';

    // Duración
    if (inicio && fin) {
        var pi = inicio.split(':'), pf = fin.split(':');
        var mins = (parseInt(pf[0], 10) * 60 + parseInt(pf[1], 10)) - (parseInt(pi[0], 10) * 60 + parseInt(pi[1], 10));
        if (mins > 0) {
            var h = Math.floor(mins / 60), m = mins % 60;
            var txt = '';
            if (h > 0) { txt += h + (h === 1 ? ' hora' : ' horas'); }
            if (m > 0) { txt += (h > 0 ? ' ' : '') + m + ' min'; }
            elDur.textContent = txt;
        } else {
            elDur.textContent = '—';
        }
    } else {
        elDur.textContent = '—';
    }
}

// Refleja la disponibilidad de la fecha elegida (hoy/mañana) en la tarjeta y el botón.
function actualizarDisponibilidad() {
    var prev = document.getElementById('equipoPreview');
    if (!prev) { return 0; }
    var sel = document.getElementById('fechaSeleccionada').value;
    var n = (sel === ahoraEcuador().fecha)
        ? parseInt(prev.dataset.dispHoy, 10)
        : parseInt(prev.dataset.dispManana, 10);
    if (isNaN(n)) { n = 0; }

    var badge = document.getElementById('equipoBadge');
    var texto = document.getElementById('equipoDispTexto');
    var btn = document.getElementById('btnSubmitReserva');
    if (badge) {
        badge.textContent = n > 0 ? 'Disponible' : 'No disponible';
        badge.classList.toggle('no-disponible', n <= 0);
    }
    if (texto) {
        texto.textContent = n > 0
            ? 'Hay equipos disponibles para reservar'
            : 'No quedan equipos para esta fecha';
    }
    if (btn) {
        btn.disabled = (n <= 0);
        btn.classList.toggle('disabled', n <= 0);
    }
    return n;
}

// Ajusta las horas por defecto según la fecha elegida:
//  - HOY  -> hora inicio = hora actual EXACTA (opción "Ahora") y se ocultan las pasadas
//  - OTRO -> horario libre (08:00 / 10:00)
function actualizarHorasPorFecha() {
    if (!window.CraiTP) { return; }
    var sel = document.getElementById('fechaSeleccionada').value;
    var ec = ahoraEcuador();
    var nowMin = ec.hora * 60 + ec.min;

    if (sel === ec.fecha && nowMin < HORA_MAX) {
        // HOY (dentro del horario): permitir desde la hora actual exacta.
        var inicioMin = Math.max(nowMin, HORA_MIN);
        var inicioStr = minutosAStr(inicioMin);
        var finMin = Math.min(inicioMin + 120, HORA_MAX);    // +2h, tope 17:00
        CraiTP.setAhora('horaInicio', inicioStr);
        CraiTP.setMin('horaInicio', inicioStr);
        CraiTP.set('horaInicio', inicioStr, false);
        CraiTP.set('horaFin', minutosAStr(finMin), false);
    } else {
        // Mañana (o ya cerró por hoy): horario libre 08:00–17:00.
        CraiTP.clearAhora('horaInicio');
        CraiTP.setMin('horaInicio', '08:00');
        CraiTP.set('horaInicio', '08:00', false);
        CraiTP.set('horaFin', '10:00', false);
    }
}

// =============================================
// ENVIAR RESERVA
// =============================================
function enviarReserva(event) {
    event.preventDefault();

    var fecha = document.getElementById('fechaSeleccionada').value;
    var inicio = document.getElementById('horaInicio').value;
    var fin = document.getElementById('horaFin').value;

    if (!fecha) { mostrarAlerta('Selecciona la fecha de uso.'); return; }
    if (fecha < ahoraEcuador().fecha) { mostrarAlerta('No puedes reservar en una fecha pasada.'); return; }
    if (fecha > fechaManana()) { mostrarAlerta('Solo puedes reservar para hoy o para mañana (máximo un día de anticipación).'); return; }
    if (!inicio || !fin) { mostrarAlerta('Selecciona la hora de inicio y la hora de fin.'); return; }
    if (fin <= inicio) { mostrarAlerta('La hora de fin debe ser mayor que la hora de inicio.'); return; }
    if (inicio < '08:00' || fin > '17:00') { mostrarAlerta('El horario de reservas es de 08:00 a 17:00.'); return; }
    if (actualizarDisponibilidad() <= 0) { mostrarAlerta('No quedan Chromebooks disponibles para esa fecha. Elige otro día.'); return; }

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
        .then(function (r) { return r.json(); })
        .then(function (data) {
            setTimeout(function () {
                document.getElementById('loaderReserva').style.display = 'none';
                if (data.success) {
                    document.getElementById('confirmacionReserva').style.display = 'block';
                    document.getElementById('codigoConfirmacion').textContent = data.codigo;
                } else {
                    form.style.display = 'block';
                    mostrarAlerta(data.message || 'No se pudo crear la reserva.');
                }
            }, 1500);
        })
        .catch(function () {
            document.getElementById('loaderReserva').style.display = 'none';
            form.style.display = 'block';
            mostrarAlerta('Error al enviar la reserva.');
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
