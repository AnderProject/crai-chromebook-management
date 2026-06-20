// =============================================
// RESERVAR CHROMEBOOK - CRAI UNEMI
// =============================================

// Slots de 30 min dentro del horario permitido (08:00–17:00)
var HORA_MIN = 8 * 60;    // 08:00 en minutos
var HORA_MAX = 17 * 60;   // 17:00 en minutos
var PASO = 30;            // intervalo de los slots del desplegable

document.addEventListener('DOMContentLoaded', function () {

    construirDropdown('dropInicio', 'horaInicio', 'valInicio');
    construirDropdown('dropFin', 'horaFin', 'valFin');
    configurarTriggers();

    // Fecha mínima = hoy (hora Ecuador); inicializa en "hoy"
    var inputFecha = document.getElementById('fechaManual');
    if (inputFecha) inputFecha.min = ahoraEcuador().fecha;
    seleccionarFecha('hoy');

    var motivo = document.querySelector('textarea[name="motivo"]');
    if (motivo) motivo.addEventListener('focus', function () { activarPaso(3); });

    // Cerrar los desplegables al hacer clic fuera
    document.addEventListener('click', function (e) {
        if (!e.target.closest('.time-select')) cerrarTodos();
    });
});

// =============================================
// UTILIDADES DE TIEMPO
// =============================================
function pad(n) { return (n < 10 ? '0' : '') + n; }
function minutosAStr(min) { return pad(Math.floor(min / 60)) + ':' + pad(min % 60); }

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
// SELECTOR DE HORA PERSONALIZADO
// =============================================
function construirDropdown(idDrop, idHidden, idVal) {
    var drop = document.getElementById(idDrop);
    if (!drop) return;
    drop.innerHTML = '';
    for (var min = HORA_MIN; min <= HORA_MAX; min += PASO) {
        drop.appendChild(crearOpcion(minutosAStr(min), minutosAStr(min), idHidden, idVal, idDrop, false));
    }
}

function crearOpcion(valor, etiqueta, idHidden, idVal, idDrop, esAhora) {
    var li = document.createElement('li');
    li.className = 'time-option' + (esAhora ? ' time-ahora' : '');
    li.setAttribute('role', 'option');
    li.dataset.valor = valor;
    if (esAhora) {
        li.innerHTML = '<i class="bi bi-clock-history me-1"></i>' + etiqueta;
    } else {
        li.textContent = etiqueta;
    }
    li.addEventListener('click', function () {
        setHora(idHidden, idVal, idDrop, valor);
        cerrarTodos();
        activarPaso(2);
    });
    return li;
}

// Opción "Ahora · HH:MM" al tope del desplegable de inicio (solo para hoy)
function inyectarAhora(idDrop, idHidden, idVal, valorExacto) {
    quitarAhora(idDrop);
    var drop = document.getElementById(idDrop);
    var li = crearOpcion(valorExacto, 'Ahora · ' + valorExacto, idHidden, idVal, idDrop, true);
    drop.insertBefore(li, drop.firstChild);
}

function quitarAhora(idDrop) {
    var drop = document.getElementById(idDrop);
    if (!drop) return;
    var ex = drop.querySelector('.time-ahora');
    if (ex) ex.remove();
}

function setHora(idHidden, idVal, idDrop, valor) {
    document.getElementById(idHidden).value = valor;
    document.getElementById(idVal).textContent = valor;
    var drop = document.getElementById(idDrop);
    drop.querySelectorAll('.time-option').forEach(function (o) {
        o.classList.toggle('seleccionado', o.dataset.valor === valor);
    });
}

function configurarTriggers() {
    [['triggerInicio', 'dropInicio'], ['triggerFin', 'dropFin']].forEach(function (par) {
        var trigger = document.getElementById(par[0]);
        if (!trigger) return;
        trigger.addEventListener('click', function (e) {
            e.stopPropagation();
            toggleDropdown(par[1], par[0]);
        });
    });
}

function toggleDropdown(idDrop, idTrigger) {
    var drop = document.getElementById(idDrop);
    var abierto = drop.classList.contains('abierto');
    cerrarTodos();
    if (!abierto) {
        drop.classList.add('abierto');
        document.getElementById(idTrigger).classList.add('activo');
        var sel = drop.querySelector('.time-option.seleccionado');
        if (sel) drop.scrollTop = sel.offsetTop - drop.clientHeight / 2 + sel.clientHeight / 2;
    }
}

function cerrarTodos() {
    ['dropInicio', 'dropFin'].forEach(function (id) {
        var d = document.getElementById(id);
        if (d) d.classList.remove('abierto');
    });
    ['triggerInicio', 'triggerFin'].forEach(function (id) {
        var t = document.getElementById(id);
        if (t) t.classList.remove('activo');
    });
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
    document.getElementById('fechaManual').value = fecha;

    document.querySelectorAll('.btn-fecha').forEach(function (b) { b.classList.remove('activo'); });
    if (typeof event !== 'undefined' && event && event.target && event.target.classList.contains('btn-fecha')) {
        event.target.classList.add('activo');
    } else {
        document.querySelector('.btn-fecha').classList.add('activo');
    }

    actualizarHorasPorFecha();
    activarPaso(1);
}

function fechaManualSeleccionada() {
    var fecha = document.getElementById('fechaManual').value;
    document.getElementById('fechaSeleccionada').value = fecha;
    document.querySelectorAll('.btn-fecha').forEach(function (b) { b.classList.remove('activo'); });
    actualizarHorasPorFecha();
    activarPaso(1);
}

// Ajusta las horas por defecto según la fecha elegida:
//  - HOY  -> hora inicio = hora actual EXACTA (con minutos) + opción "Ahora"
//  - OTRO -> horario libre (08:00 / 10:00)
function actualizarHorasPorFecha() {
    var sel = document.getElementById('fechaSeleccionada').value;
    var ec = ahoraEcuador();

    if (sel === ec.fecha) {
        var nowMin = ec.hora * 60 + ec.min;
        if (nowMin >= HORA_MAX) {
            // Ya cerró por hoy: deja el horario libre (elegirá otro día)
            quitarAhora('dropInicio');
            setHora('horaInicio', 'valInicio', 'dropInicio', '08:00');
            setHora('horaFin', 'valFin', 'dropFin', '10:00');
            return;
        }
        var inicioMin = Math.max(nowMin, HORA_MIN);          // exacto, con minutos
        var finMin = Math.min(inicioMin + 120, HORA_MAX);    // +2h, tope 17:00
        if (finMin <= inicioMin) finMin = HORA_MAX;
        var inicioStr = minutosAStr(inicioMin);
        inyectarAhora('dropInicio', 'horaInicio', 'valInicio', inicioStr);
        setHora('horaInicio', 'valInicio', 'dropInicio', inicioStr);
        setHora('horaFin', 'valFin', 'dropFin', minutosAStr(finMin));
    } else {
        quitarAhora('dropInicio');
        setHora('horaInicio', 'valInicio', 'dropInicio', '08:00');
        setHora('horaFin', 'valFin', 'dropFin', '10:00');
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
    if (!inicio || !fin) { mostrarAlerta('Selecciona la hora de inicio y la hora de fin.'); return; }
    if (fin <= inicio) { mostrarAlerta('La hora de fin debe ser mayor que la hora de inicio.'); return; }
    if (inicio < '08:00' || fin > '17:00') { mostrarAlerta('El horario de reservas es de 08:00 a 17:00.'); return; }

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
