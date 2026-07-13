// =============================================
// CHATBOT IA - CRAI UNEMI
// Asistente virtual para estudiantes
// =============================================

var CHAT_STORAGE_KEY = 'crai_chat_historial';

function toggleChatbot() {
    var ventana = document.getElementById('chatbotVentana');
    ventana.classList.toggle('abierta');
    if (ventana.classList.contains('abierta')) {
        var cont = document.getElementById('chatbotMensajes');
        cont.scrollTop = cont.scrollHeight;
    }
}

function enviarMensaje(event) {
    if (event.key === 'Enter') {
        procesarMensaje();
    }
}

// ---- Utilidades de formato ----
function escaparHtml(texto) {
    var div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
}

// Convierte el texto del bot a HTML seguro: saltos de línea y *negritas*
function formatearBot(texto) {
    var seguro = escaparHtml(texto);
    seguro = seguro.replace(/\*(.+?)\*/g, '<strong>$1</strong>');
    seguro = seguro.replace(/\n/g, '<br>');
    return seguro;
}

function horaActual() {
    return new Date().toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' });
}

// ---- Persistencia (sessionStorage: dura solo la sesión del navegador) ----
function leerHistorial() {
    try {
        return JSON.parse(sessionStorage.getItem(CHAT_STORAGE_KEY)) || [];
    } catch (e) {
        return [];
    }
}

function guardarEnHistorial(tipo, texto, hora) {
    var hist = leerHistorial();
    hist.push({ tipo: tipo, texto: texto, hora: hora });
    sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(hist));
}

// ---- Render de mensajes ----
function agregarMensaje(tipo, texto, hora, guardar) {
    var contenedor = document.getElementById('chatbotMensajes');
    var div = document.createElement('div');
    div.className = tipo === 'usuario' ? 'mensaje-usuario' : 'mensaje-bot';

    var contenido = tipo === 'usuario' ? escaparHtml(texto) : formatearBot(texto);
    div.innerHTML =
        '<div class="mensaje-contenido">' + contenido +
        '<span class="mensaje-hora">' + (hora || '') + '</span></div>';

    contenedor.appendChild(div);
    contenedor.scrollTop = contenedor.scrollHeight;

    if (guardar) {
        guardarEnHistorial(tipo, texto, hora);
    }
    return div;
}

function mostrarEscribiendo() {
    var contenedor = document.getElementById('chatbotMensajes');
    var div = document.createElement('div');
    div.className = 'mensaje-bot';
    div.innerHTML =
        '<div class="mensaje-contenido chatbot-typing">' +
        '<span></span><span></span><span></span></div>';
    contenedor.appendChild(div);
    contenedor.scrollTop = contenedor.scrollHeight;
    return div;
}

function ocultarChips() {
    var chips = document.getElementById('chatbotChips');
    if (chips) chips.style.display = 'none';
}

function sugerencia(texto) {
    var input = document.getElementById('chatbotInput');
    input.value = texto;
    procesarMensaje();
}

function procesarMensaje() {
    var input = document.getElementById('chatbotInput');
    var mensaje = input.value.trim();
    if (!mensaje) return;

    ocultarChips();
    agregarMensaje('usuario', mensaje, horaActual(), true);
    input.value = '';

    var escribiendo = mostrarEscribiendo();

    fetch('/estudiantes/api/chatbot/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensaje: mensaje }),
    })
    .then(function (res) { return res.json(); })
    .then(function (data) {
        escribiendo.remove();
        var accion = data.accion;
        // Modo asesoría humana: el bot queda en silencio; responde el asesor.
        if (accion === 'asesoria_humana') { iniciarAsesoria(false); return; }
        var respuesta = data.respuesta || 'Error al procesar el mensaje.';
        agregarMensaje('bot', respuesta, horaActual(), true);
        if (accion === 'solicitar_asesoria') { iniciarAsesoria(true); }
        else if (accion === 'asesoria_cerrada') { detenerAsesoria(); }
        // Si el bot ejecutó una acción que cambia los datos, refrescar la actividad
        if (accion === 'reservar' || accion === 'cancelar') {
            refrescarActividad();
        }
    })
    .catch(function () {
        escribiendo.remove();
        agregarMensaje('bot', 'Error de conexión. Intenta de nuevo.', horaActual(), true);
    });
}

function limpiarChat() {
    sessionStorage.removeItem(CHAT_STORAGE_KEY);
    var contenedor = document.getElementById('chatbotMensajes');
    // Conservar solo el primer mensaje (bienvenida estática)
    while (contenedor.children.length > 1) {
        contenedor.removeChild(contenedor.lastChild);
    }
    var chips = document.getElementById('chatbotChips');
    if (chips) chips.style.display = '';
}

function cargarHistorial() {
    var hist = leerHistorial();
    if (!hist.length) return;
    var hayUsuario = false;
    hist.forEach(function (m) {
        agregarMensaje(m.tipo, m.texto, m.hora, false);
        if (m.tipo === 'usuario') hayUsuario = true;
    });
    if (hayUsuario) ocultarChips();
}

// ---- Aviso: faltan 15 min para devolver el Chromebook ----
var AVISOS_KEY = 'crai_avisos_devolucion';
function leerAvisosMostrados() {
    try { return JSON.parse(sessionStorage.getItem(AVISOS_KEY)) || {}; }
    catch (e) { return {}; }
}
function procesarAvisosDevolucion(avisos) {
    if (!avisos || !avisos.length) return;
    var mostrados = leerAvisosMostrados();
    var nuevos = false;
    avisos.forEach(function (a) {
        if (mostrados[a.id]) return;          // ya avisado en esta sesión
        mostrados[a.id] = true;
        nuevos = true;
        var equipo = a.chromebook ? ' ' + a.chromebook : '';
        var texto = '⏰ Te quedan ' + a.minutos + ' min para devolver tu Chromebook' +
            equipo + ' (hasta las ' + a.hora + '). ¡No olvides entregarlo a tiempo!';
        if (typeof mostrarToast === 'function') {
            mostrarToast(texto, 'warning');
        }
        // También lo dejamos como mensaje del asistente en el chat.
        if (document.getElementById('chatbotMensajes')) {
            agregarMensaje('bot', texto, horaActual(), true);
        }
    });
    if (nuevos) {
        sessionStorage.setItem(AVISOS_KEY, JSON.stringify(mostrados));
    }
}

// ---- Asesoría humana (handoff): recibir mensajes del asesor ----
var ASESOR_ID_KEY = 'crai_asesor_ultimo_id';
var asesoriaTimer = null;

function getUltimoAsesorId() { return parseInt(sessionStorage.getItem(ASESOR_ID_KEY) || '0', 10) || 0; }
function setUltimoAsesorId(v) { sessionStorage.setItem(ASESOR_ID_KEY, String(v)); }

function mostrarBannerAsesoria() {
    if (document.getElementById('chatAsesorBanner')) return;
    var cont = document.getElementById('chatbotMensajes');
    if (!cont || !cont.parentNode) return;
    var b = document.createElement('div');
    b.id = 'chatAsesorBanner';
    b.className = 'chat-asesor-banner';
    b.innerHTML = '<i class="bi bi-headset"></i> Estás hablando con un asesor del CRAI. ' +
        'Escribe <strong>"salir"</strong> para volver al asistente.';
    cont.parentNode.insertBefore(b, cont);
}
function quitarBannerAsesoria() {
    var b = document.getElementById('chatAsesorBanner');
    if (b) b.remove();
}

function iniciarAsesoria(mostrarBanner) {
    if (mostrarBanner) mostrarBannerAsesoria();
    if (asesoriaTimer) return;
    asesoriaTimer = setInterval(pollAsesoria, 4000);
    pollAsesoria();
}
function detenerAsesoria() {
    if (asesoriaTimer) { clearInterval(asesoriaTimer); asesoriaTimer = null; }
    quitarBannerAsesoria();
    setUltimoAsesorId(0);
}
function pollAsesoria() {
    fetch('/estudiantes/api/asesoria/mis-mensajes/?desde=' + getUltimoAsesorId(),
          { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(function (r) { return r.json(); })
    .then(function (d) {
        if (!d.activa) {
            if (asesoriaTimer) {
                agregarMensaje('bot', '✅ El asesor finalizó la conversación. Sigo yo por aquí 🤖', horaActual(), true);
            }
            detenerAsesoria();
            return;
        }
        mostrarBannerAsesoria();
        (d.mensajes || []).forEach(function (m) {
            agregarMensaje('bot', '👩‍💼 ' + m.texto, m.hora, true);
        });
        if (d.ultimo_id) setUltimoAsesorId(d.ultimo_id);
    })
    .catch(function () { /* silencioso */ });
}

// ---- Actualización en tiempo real de "Actividad reciente" ----
var ultimaActividadHtml = null;
function refrescarActividad() {
    var lista = document.querySelector('.actividad-lista');
    if (!lista) return;
    fetch('/estudiantes/api/actividad/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            // Solo reemplazar si CAMBIÓ (evita el parpadeo en el refresco periódico)
            if (data.html && data.html !== ultimaActividadHtml) {
                lista.innerHTML = data.html;
                ultimaActividadHtml = data.html;
            }
            var badge = document.querySelector('[data-disponibles]');
            if (badge && typeof data.disponibles !== 'undefined') {
                badge.setAttribute('data-disponibles', data.disponibles);
                var hay = data.disponibles > 0;
                badge.classList.toggle('dispo-hay', hay);
                badge.classList.toggle('dispo-no', !hay);
                var txt = badge.querySelector('.dispo-txt');
                if (txt) txt.textContent = hay ? 'Chromebooks disponibles' : 'Sin Chromebooks disponibles';
                var ico = badge.querySelector('.dispo-ico');
                if (ico) ico.className = 'bi dispo-ico ' + (hay ? 'bi-check-circle-fill' : 'bi-x-circle-fill');
            }
            procesarAvisosDevolucion(data.avisos_devolucion);
        })
        .catch(function () { /* silencioso */ });
}

function comprobarAsesoriaAlCargar() {
    if (!document.getElementById('chatbotMensajes')) return;
    fetch('/estudiantes/api/asesoria/mis-mensajes/?desde=' + getUltimoAsesorId(),
          { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(function (r) { return r.json(); })
    .then(function (d) { if (d.activa) { iniciarAsesoria(true); } })
    .catch(function () { /* silencioso */ });
}

document.addEventListener('DOMContentLoaded', function () {
    cargarHistorial();
    comprobarAsesoriaAlCargar();
    // Refresco periódico por si hay cambios desde otros canales (admin, etc.)
    // y para detectar préstamos próximos a vencer (aviso de 15 min).
    if (document.querySelector('.actividad-lista')) {
        refrescarActividad();
        setInterval(refrescarActividad, 30000);
    }
});
