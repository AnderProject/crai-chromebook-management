// =============================================
// TOAST FLOTANTE - CRAI UNEMI
// Confirmaciones de acciones. API global:
//   mostrarToast(texto, tipo)            -> muestra un toast ahora
//   mostrarToastTrasReload(texto, tipo)  -> lo muestra tras location.reload()
// tipo: 'success' | 'error' | 'warning' | 'info'
// =============================================

(function () {
    var ICONOS = {
        success: 'bi-check-circle-fill',
        error: 'bi-x-circle-fill',
        warning: 'bi-exclamation-triangle-fill',
        info: 'bi-info-circle-fill'
    };
    var DURACION = 4000;
    var CLAVE_RELOAD = 'craiToastPendiente';

    function limpiarTexto(texto) {
        // Quita el emoji inicial (✅/❌/⚠️/ℹ️); el color e icono ya indican el tipo.
        return String(texto).replace(/^\s*[✅❌⚠️ℹ\s]+/, '').trim();
    }

    function mostrarToast(texto, tipo) {
        tipo = ICONOS[tipo] ? tipo : 'info';
        var cont = document.getElementById('toastContainer');
        if (!cont) { return; }

        var el = document.createElement('div');
        el.className = 'toast-crai toast-' + tipo;
        el.setAttribute('role', 'alert');

        var icono = document.createElement('i');
        icono.className = 'bi ' + ICONOS[tipo] + ' toast-crai-icono';

        var span = document.createElement('span');
        span.className = 'toast-crai-texto';
        span.textContent = limpiarTexto(texto); // textContent evita XSS

        var cerrar = document.createElement('button');
        cerrar.type = 'button';
        cerrar.className = 'toast-crai-cerrar';
        cerrar.setAttribute('aria-label', 'Cerrar');
        cerrar.innerHTML = '&times;';

        el.appendChild(icono);
        el.appendChild(span);
        el.appendChild(cerrar);
        cont.appendChild(el);

        requestAnimationFrame(function () { el.classList.add('visible'); });

        var temporizador;
        function ocultar() {
            clearTimeout(temporizador);
            el.classList.remove('visible');
            el.addEventListener('transitionend', function () {
                if (el.parentNode) { el.parentNode.removeChild(el); }
            }, { once: true });
        }

        cerrar.addEventListener('click', ocultar);
        temporizador = setTimeout(ocultar, DURACION);
    }

    function mostrarToastTrasReload(texto, tipo) {
        try {
            sessionStorage.setItem(CLAVE_RELOAD, JSON.stringify({ texto: texto, tipo: tipo || 'info' }));
        } catch (e) { /* sessionStorage no disponible: se ignora */ }
    }

    document.addEventListener('DOMContentLoaded', function () {
        // 1) Toast que sobrevive a un reload (acciones AJAX).
        try {
            var pendiente = sessionStorage.getItem(CLAVE_RELOAD);
            if (pendiente) {
                sessionStorage.removeItem(CLAVE_RELOAD);
                var p = JSON.parse(pendiente);
                mostrarToast(p.texto, p.tipo);
            }
        } catch (e) { /* ignorar */ }

        // 2) Mensajes del framework de Django renderizados en el HTML.
        var box = document.getElementById('djangoMessages');
        if (box) {
            var msgs = box.querySelectorAll('.dj-msg');
            for (var i = 0; i < msgs.length; i++) {
                (function (m, idx) {
                    setTimeout(function () {
                        mostrarToast(m.textContent, m.getAttribute('data-tipo'));
                    }, idx * 150);
                })(msgs[i], i);
            }
        }
    });

    window.mostrarToast = mostrarToast;
    window.mostrarToastTrasReload = mostrarToastTrasReload;
})();
