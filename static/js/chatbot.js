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
        var respuesta = data.respuesta || 'Error al procesar el mensaje.';
        agregarMensaje('bot', respuesta, horaActual(), true);
        // Si el bot ejecutó una acción que cambia los datos, refrescar la actividad
        if (data.accion === 'reservar' || data.accion === 'cancelar') {
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
            var disp = document.querySelector('[data-disponibles]');
            if (disp && typeof data.disponibles !== 'undefined') {
                disp.textContent = data.disponibles;
            }
        })
        .catch(function () { /* silencioso */ });
}

document.addEventListener('DOMContentLoaded', function () {
    cargarHistorial();
    // Refresco periódico por si hay cambios desde otros canales (admin, etc.)
    if (document.querySelector('.actividad-lista')) {
        setInterval(refrescarActividad, 30000);
    }
});
