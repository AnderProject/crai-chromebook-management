// =============================================
// CHATBOT IA - CRAI UNEMI
// Asistente virtual para estudiantes
// =============================================

function toggleChatbot() {
    const ventana = document.getElementById('chatbotVentana');
    ventana.classList.toggle('abierta');
}

function enviarMensaje(event) {
    if (event.key === 'Enter') {
        procesarMensaje();
    }
}

function procesarMensaje() {
    const input = document.getElementById('chatbotInput');
    const mensaje = input.value.trim();
    
    if (!mensaje) return;
    
    // Mostrar mensaje del usuario
    agregarMensaje('usuario', mensaje);
    input.value = '';
    
    // Simular respuesta del bot (luego conectaremos con Gemini)
    setTimeout(function() {
        const respuesta = generarRespuesta(mensaje.toLowerCase());
        agregarMensaje('bot', respuesta);
    }, 800);
}

function agregarMensaje(tipo, texto) {
    const contenedor = document.getElementById('chatbotMensajes');
    const div = document.createElement('div');
    div.className = tipo === 'usuario' ? 'mensaje-usuario' : 'mensaje-bot';
    div.innerHTML = `<div class="mensaje-contenido">${texto}</div>`;
    contenedor.appendChild(div);
    contenedor.scrollTop = contenedor.scrollHeight;
}

function generarRespuesta(mensaje) {
    if (mensaje.includes('disponible') || mensaje.includes('hay') || mensaje.includes('libre')) {
        return 'Actualmente hay <strong>12 Chromebooks disponibles</strong> de 48 en total. 📊<br><br>¿Quieres que te reserve uno?';
    } else if (mensaje.includes('reservar') || mensaje.includes('prestar') || mensaje.includes('pedir')) {
        return '¡Claro! Para reservar un Chromebook necesito:<br><br>📅 ¿Para qué día y hora lo necesitas?<br>⏰ ¿Por cuántas horas? (2, 4 u 8)';
    } else if (mensaje.includes('reserva') || mensaje.includes('pendiente') || mensaje.includes('mis')) {
        return 'Tienes <strong>1 préstamo activo</strong>:<br><br>💻 CB-015 - HP 11 G8<br>⏰ Vence hoy a las 18:00<br><br>¿Necesitas algo más?';
    } else if (mensaje.includes('hora') || mensaje.includes('tiempo') || mensaje.includes('cuánto')) {
        return 'Puedes prestar un Chromebook por:<br><br>⏰ 2 horas<br>⏰ 4 horas<br>⏰ 8 horas<br><br>Renovable si no hay reservas.';
    } else if (mensaje.includes('hola') || mensaje.includes('buenos') || mensaje.includes('gracias')) {
        return '¡Hola! 😊 ¿En qué puedo ayudarte hoy? Recuerda que puedes preguntarme sobre disponibilidad, reservas y horarios.';
    } else {
        return 'No entendí bien. Puedes preguntarme sobre:<br><br>💻 Disponibilidad de equipos<br>📅 Reservar Chromebook<br>📋 Estado de tus reservas<br>⏰ Horarios de préstamo';
    }
}