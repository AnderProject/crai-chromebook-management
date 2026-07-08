// =============================================
// Portal de Técnicos · CRAI UNEMI — panel
// Confirmación de reparación (modal propio), overlay de
// carga al enviar y notificación flotante de resultado.
// =============================================
var _formPendiente = null;

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
