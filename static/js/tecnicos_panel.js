// =============================================
// Portal de Técnicos · CRAI UNEMI — panel
// Confirmación de reparación (modal propio), overlay de
// carga al enviar y notificación flotante de resultado.
// =============================================
var _formPendiente = null;

// Despliega/oculta el formulario de evidencia de una tarjeta (acordeón horizontal).
function tecToggleForm(btn) {
    var card = btn.closest('.tec-card');
    if (!card) { return; }
    var wrap = card.querySelector('.tec-form-wrap');
    if (!wrap) { return; }
    var abrir = wrap.hasAttribute('hidden');
    wrap.hidden = !abrir;
    btn.setAttribute('aria-expanded', abrir ? 'true' : 'false');
    if (abrir) {
        var ta = wrap.querySelector('textarea');
        if (ta) { ta.focus(); }
    }
}

// Muestra la evidencia (foto o video) en un modal, sin abrir otra pestaña.
function tecVerEvidencia(url) {
    var visor = document.getElementById('tecEviVisor');
    if (!visor) { return; }
    var esVideo = /\.(mp4|webm|mov|ogg)(\?|$)/i.test(url);
    visor.innerHTML = esVideo
        ? '<video src="' + url + '" controls autoplay playsinline class="tec-evi-full"></video>'
        : '<img src="' + url + '" alt="Evidencia de la reparación" class="tec-evi-full">';
    document.getElementById('modalEvidencia').classList.add('visible');
}

function tecCerrarEvidencia() {
    var m = document.getElementById('modalEvidencia');
    if (m) { m.classList.remove('visible'); }
    var visor = document.getElementById('tecEviVisor');
    if (visor) { visor.innerHTML = ''; }   // detiene el video al cerrar
}

function pedirConfirmacion(btn) {
    var form = btn.closest('form');
    if (!form.reportValidity()) return;   // valida descripción + evidencia
    _formPendiente = form;
    document.getElementById('confEquipo').textContent = btn.dataset.equipo || 'seleccionado';
    document.getElementById('modalConfirmar').classList.add('visible');
}

function cerrarConfirmar() {
    document.getElementById('modalConfirmar').classList.remove('visible');
    _formPendiente = null;
}

function enviarConfirmacion() {
    if (!_formPendiente) return;
    document.getElementById('modalConfirmar').classList.remove('visible');
    document.getElementById('tecLoading').classList.add('visible');
    _formPendiente.submit();
}

document.addEventListener('DOMContentLoaded', function () {
    // Cerrar el modal de confirmar al hacer clic fuera
    var modal = document.getElementById('modalConfirmar');
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === this) cerrarConfirmar();
        });
    }

    // Tecla Escape: cierra el visor de evidencia y el modal de confirmar
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { tecCerrarEvidencia(); cerrarConfirmar(); }
    });

    // Mensajes del servidor → modal flotante (en vez de banner)
    var data = document.querySelector('.tec-flash-data');
    if (!data) return;
    var flash = document.getElementById('tecFlash');
    var esError = data.dataset.tipo === 'error';
    flash.classList.toggle('flash-error', esError);
    flash.querySelector('.tec-flash-ico i').className = esError ? 'bi bi-exclamation-circle-fill' : 'bi bi-check-circle-fill';
    flash.querySelector('.tec-flash-msg').textContent = data.dataset.msg;
    flash.classList.add('visible');
    setTimeout(function () { flash.classList.remove('visible'); }, 5000);
});
