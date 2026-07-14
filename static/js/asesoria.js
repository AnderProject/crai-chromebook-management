// =============================================
// ASESORÍA EN VIVO (panel del asesor) - CRAI UNEMI
// Handoff del chatbot a un asesor real: polling de solicitudes,
// aviso con sonido y conversación con el estudiante (web/WhatsApp).
// =============================================
(function () {
    var fab = document.getElementById('asesoriaFab');
    if (!fab) return;   // solo en el panel administrativo

    var URL_PEND = '/prestamos/api/asesoria/pendientes/';
    var panel = document.getElementById('asesoriaPanel');
    var badge = document.getElementById('asesoriaFabBadge');
    var lista = document.getElementById('asesoriaLista');
    var vistaLista = document.getElementById('asesoriaVistaLista');
    var vistaChat = document.getElementById('asesoriaVistaChat');
    var contMsgs = document.getElementById('asesoriaMensajes');

    var currentId = null;         // asesoría abierta
    var ultimoNoLeidos = 0;       // para detectar mensajes nuevos y sonar
    var chatTimer = null;
    var asesoriaTab = 'activas';  // 'activas' | 'historial'

    // ---------- utilidades ----------
    function getCookie(name) {
        var v = document.cookie.split(';');
        for (var i = 0; i < v.length; i++) {
            var c = v[i].trim();
            if (c.indexOf(name + '=') === 0) return c.substring(name.length + 1);
        }
        return '';
    }
    function esc(t) { var d = document.createElement('div'); d.textContent = t || ''; return d.innerHTML; }

    // Tono de aviso con Web Audio (sin archivo de sonido)
    function sonar() {
        try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) return;
            var ctx = new Ctx();
            [0, 0.18].forEach(function (t) {
                var o = ctx.createOscillator(), g = ctx.createGain();
                o.type = 'sine';
                o.frequency.value = t === 0 ? 880 : 1175;
                g.gain.setValueAtTime(0.0001, ctx.currentTime + t);
                g.gain.exponentialRampToValueAtTime(0.25, ctx.currentTime + t + 0.03);
                g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + t + 0.16);
                o.connect(g); g.connect(ctx.destination);
                o.start(ctx.currentTime + t); o.stop(ctx.currentTime + t + 0.18);
            });
            setTimeout(function () { ctx.close(); }, 800);
        } catch (e) { /* sin audio */ }
    }

    // ---------- panel ----------
    window.asesoriaTogglePanel = function () {
        var abierto = panel.classList.toggle('abierto');
        panel.setAttribute('aria-hidden', abierto ? 'false' : 'true');
        if (abierto) { asesoriaVolverLista(); cargarPendientes(); }
    };
    window.asesoriaVolverLista = function () {
        currentId = null;
        if (chatTimer) { clearInterval(chatTimer); chatTimer = null; }
        vistaChat.hidden = true;
        vistaLista.hidden = false;
        if (asesoriaTab === 'historial') cargarHistorial(); else cargarPendientes();
    };

    window.asesoriaCambiarTab = function (tab) {
        asesoriaTab = tab;
        document.getElementById('asesoriaTabActivas').classList.toggle('activa', tab === 'activas');
        document.getElementById('asesoriaTabHistorial').classList.toggle('activa', tab === 'historial');
        if (tab === 'historial') cargarHistorial(); else cargarPendientes();
    };

    function cargarHistorial() {
        lista.innerHTML = '<div class="asesoria-vacio"><i class="bi bi-hourglass"></i><p>Cargando…</p></div>';
        fetch('/prestamos/api/asesoria/historial/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d.ok) return;
                if (!(d.solicitudes || []).length) {
                    lista.innerHTML = '<div class="asesoria-vacio"><i class="bi bi-clock-history"></i><p>Sin conversaciones anteriores</p></div>';
                    return;
                }
                pintarLista(d.solicitudes);
            })
            .catch(function () {});
    }

    // ---------- lista de solicitudes ----------
    function cargarPendientes() {
        fetch(URL_PEND, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d.ok) return;
                // Badge = total de mensajes sin leer
                if (d.no_leidos > 0) { badge.textContent = d.no_leidos; badge.hidden = false; fab.classList.add('con-aviso'); }
                else { badge.hidden = true; fab.classList.remove('con-aviso'); }
                // Sonar si aumentaron los no leídos (mensaje/solicitud nueva)
                if (d.no_leidos > ultimoNoLeidos) { sonar(); }
                ultimoNoLeidos = d.no_leidos;
                // Render de la lista solo si estamos en la vista de activas
                if (!vistaLista.hidden && asesoriaTab === 'activas') pintarLista(d.solicitudes || []);
            })
            .catch(function () { /* silencioso */ });
    }

    function pintarLista(sols) {
        if (!sols.length) {
            lista.innerHTML = '<div class="asesoria-vacio"><i class="bi bi-cup-hot"></i><p>No hay solicitudes de asesoría</p></div>';
            return;
        }
        lista.innerHTML = sols.map(function (s) {
            var canalIco = s.canal === 'whatsapp' ? 'bi-whatsapp' : 'bi-globe';
            var nl = s.no_leidos > 0 ? '<span class="asesoria-item-badge">' + s.no_leidos + '</span>' : '';
            return '<button type="button" class="asesoria-item' + (s.no_leidos > 0 ? ' no-leido' : '') +
                '" onclick="asesoriaAbrir(' + s.id + ')">' +
                '<span class="asesoria-item-avatar"><i class="bi bi-person-fill"></i></span>' +
                '<span class="asesoria-item-cuerpo">' +
                '<span class="asesoria-item-top"><strong>' + esc(s.nombre) + '</strong>' + nl + '</span>' +
                '<span class="asesoria-item-msg">' + esc(s.ultimo || '—') + '</span></span>' +
                '<span class="asesoria-item-canal"><i class="bi ' + canalIco + '"></i></span>' +
                '</button>';
        }).join('');
    }

    // ---------- conversación ----------
    window.asesoriaAbrir = function (id) {
        currentId = id;
        vistaLista.hidden = true;
        vistaChat.hidden = false;
        contMsgs.innerHTML = '';
        cargarMensajes(true);
        if (chatTimer) clearInterval(chatTimer);
        chatTimer = setInterval(function () { cargarMensajes(false); cargarPendientes(); }, 4000);
    };

    function cargarMensajes(scroll) {
        if (!currentId) return;
        fetch('/prestamos/api/asesoria/' + currentId + '/mensajes/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d.ok) return;
                document.getElementById('asesoriaChatNombre').textContent = d.nombre || 'Estudiante';
                document.getElementById('asesoriaChatCanal').innerHTML =
                    (d.canal === 'whatsapp' ? '<i class="bi bi-whatsapp"></i> WhatsApp' : '<i class="bi bi-globe"></i> Chat web') +
                    (d.estado === 'pendiente' ? ' · <span class="asesoria-pend">nueva</span>' : '');
                // Conversación cerrada: solo lectura (sin enviar ni finalizar).
                var cerrada = (d.estado === 'cerrada');
                document.getElementById('asesoriaInputWrap').hidden = cerrada;
                document.getElementById('asesoriaFinalizarBtn').hidden = cerrada;
                document.getElementById('asesoriaCerradaAviso').hidden = !cerrada;
                if (cerrada && chatTimer) { clearInterval(chatTimer); chatTimer = null; }
                contMsgs.innerHTML = (d.mensajes || []).map(function (m) {
                    var cls = m.remitente === 'asesor' ? 'asesor' : 'estudiante';
                    return '<div class="asesoria-msg ' + cls + '"><div class="asesoria-burbuja">' +
                        esc(m.texto) + '<span class="asesoria-msg-hora">' + m.hora + '</span></div></div>';
                }).join('');
                if (scroll) contMsgs.scrollTop = contMsgs.scrollHeight;
                else if (contMsgs.scrollHeight - contMsgs.scrollTop - contMsgs.clientHeight < 120) contMsgs.scrollTop = contMsgs.scrollHeight;
            })
            .catch(function () {});
    }

    window.asesoriaEnviar = function () {
        var input = document.getElementById('asesoriaInput');
        var texto = input.value.trim();
        if (!texto || !currentId) return;
        input.value = '';
        fetch('/prestamos/api/asesoria/' + currentId + '/responder/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ texto: texto }),
        })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (d.ok) cargarMensajes(true); })
        .catch(function () {});
    };

    window.asesoriaFinalizar = function () {
        if (!currentId) return;
        fetch('/prestamos/api/asesoria/' + currentId + '/cerrar/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (d.ok) asesoriaVolverLista(); })
        .catch(function () {});
    };

    // ---------- arranque: polling de fondo ----------
    cargarPendientes();
    setInterval(cargarPendientes, 6000);
})();
