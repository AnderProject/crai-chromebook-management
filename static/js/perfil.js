// =============================================
// PERFIL (admin y estudiante) - CRAI UNEMI
// Edición de celular + cambio de contraseña con código de verificación por correo.
// Comparte los mismos IDs en ambas plantillas y los endpoints de /prestamos/api/perfil/.
// =============================================

(function () {
    var URL_TELEFONO = '/prestamos/api/perfil/telefono/';
    var URL_PWD_SOLICITAR = '/prestamos/api/perfil/password/solicitar/';
    var URL_PWD_CONFIRMAR = '/prestamos/api/perfil/password/confirmar/';

    function getCSRFToken() {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var c = cookies[i].trim();
            if (c.startsWith('csrftoken=')) return c.substring('csrftoken='.length);
        }
        return '';
    }

    function postJSON(url, body) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify(body)
        }).then(function (r) { return r.json(); });
    }

    function aviso(mensaje, tipo) {
        if (typeof mostrarToast === 'function') { mostrarToast(mensaje, tipo); }
        else { alert(mensaje); }
    }

    function ocupar(btn, ocupado, textoOcupado) {
        if (!btn) return;
        if (ocupado) {
            btn.dataset.html = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>' + (textoOcupado || 'Procesando...');
        } else {
            btn.disabled = false;
            if (btn.dataset.html) { btn.innerHTML = btn.dataset.html; }
        }
    }

    // ---------- Editar celular (edición inline junto al dato) ----------
    function mostrarEdicionTelefono(mostrar) {
        var vista = document.getElementById('telefonoVista');
        var form = document.getElementById('telefonoForm');
        if (!vista || !form) { return; }
        vista.hidden = mostrar;
        form.hidden = !mostrar;
        if (mostrar) {
            var input = document.getElementById('inputTelefono');
            if (input) { input.focus(); input.select(); }
        }
    }

    function cancelarEdicionTelefono() {
        var input = document.getElementById('inputTelefono');
        var disp = document.getElementById('telefonoActual');
        if (input && disp) {
            var actual = (disp.textContent || '').replace(/\D/g, '');
            input.value = actual;
        }
        mostrarEdicionTelefono(false);
    }

    function guardarTelefono() {
        var input = document.getElementById('inputTelefono');
        var btn = document.getElementById('btnGuardarTelefono');
        if (!input) return;
        var telefono = input.value.replace(/\D/g, '');
        if (telefono && telefono.length !== 10) {
            aviso('El celular debe tener 10 dígitos.', 'warning');
            return;
        }
        ocupar(btn, true, '');
        postJSON(URL_TELEFONO, { telefono: telefono })
            .then(function (data) {
                ocupar(btn, false);
                if (data.success) {
                    input.value = telefono;
                    var disp = document.getElementById('telefonoActual');
                    if (disp) { disp.textContent = data.telefono || '—'; }
                    mostrarEdicionTelefono(false);
                    aviso(data.message || 'Celular actualizado.', 'success');
                } else {
                    aviso(data.message || 'No se pudo actualizar.', 'error');
                }
            })
            .catch(function () { ocupar(btn, false); aviso('Error de conexión.', 'error'); });
    }

    // ---------- Cambio de contraseña con código ----------
    function solicitarCodigo() {
        var actual = (document.getElementById('inputPwdActual') || {}).value || '';
        var nueva = (document.getElementById('inputPwdNueva') || {}).value || '';
        var confirmar = (document.getElementById('inputPwdConfirmar') || {}).value || '';
        var btn = document.getElementById('btnEnviarCodigoPwd');
        var btnReenviar = document.getElementById('btnReenviarCodigoPwd');

        if (nueva.length < 8) { aviso('La nueva contraseña debe tener al menos 8 caracteres.', 'warning'); return; }
        if (nueva !== confirmar) { aviso('La confirmación no coincide con la nueva contraseña.', 'warning'); return; }

        var btnActivo = (this === btnReenviar) ? btnReenviar : btn;
        ocupar(btnActivo, true, 'Enviando...');
        postJSON(URL_PWD_SOLICITAR, { actual: actual, nueva: nueva, confirmar: confirmar })
            .then(function (data) {
                ocupar(btnActivo, false);
                if (data.success) {
                    var destino = document.getElementById('pwdCorreoDestino');
                    if (destino) { destino.textContent = data.correo || 'tu correo'; }
                    document.getElementById('pasoPwd1').style.display = 'none';
                    document.getElementById('pasoPwd2').style.display = 'block';
                    var cod = document.getElementById('inputPwdCodigo');
                    if (cod) { cod.value = ''; cod.focus(); }
                    aviso(data.message || 'Código enviado.', 'success');
                } else {
                    aviso(data.message || 'No se pudo enviar el código.', 'error');
                }
            })
            .catch(function () { ocupar(btnActivo, false); aviso('Error de conexión.', 'error'); });
    }

    var pwdConfirmando = false;  // evita envíos duplicados (clic + autoconfirmación)

    function confirmarCodigo() {
        if (pwdConfirmando) { return; }
        var input = document.getElementById('inputPwdCodigo');
        var codigo = (input || {}).value || '';
        var btn = document.getElementById('btnConfirmarCodigoPwd');
        var hint = document.getElementById('pwdCodigoHint');
        if (!codigo.trim()) { aviso('Ingresa el código que recibiste por correo.', 'warning'); return; }

        pwdConfirmando = true;
        ocupar(btn, true, 'Verificando...');
        if (hint) { hint.innerHTML = '<i class="bi bi-hourglass-split"></i> Verificando código…'; }
        postJSON(URL_PWD_CONFIRMAR, { codigo: codigo.trim() })
            .then(function (data) {
                pwdConfirmando = false;
                ocupar(btn, false);
                if (data.success) {
                    if (hint) { hint.innerHTML = '<i class="bi bi-check-circle"></i> ¡Verificado!'; }
                    aviso(data.message || 'Contraseña actualizada.', 'success');
                    reiniciarFormularioPwd();
                } else {
                    aviso(data.message || 'Código incorrecto.', 'error');
                    // Limpiar para reintentar; la autoconfirmación se vuelve a disparar al completar 6 dígitos.
                    if (input) { input.value = ''; input.focus(); }
                    if (hint) { hint.innerHTML = '<i class="bi bi-exclamation-circle text-danger"></i> Código incorrecto, intenta de nuevo'; }
                }
            })
            .catch(function () {
                pwdConfirmando = false;
                ocupar(btn, false);
                aviso('Error de conexión.', 'error');
                if (hint) { hint.innerHTML = '<i class="bi bi-info-circle"></i> Ingresa los 6 dígitos'; }
            });
    }

    function reiniciarFormularioPwd() {
        ['inputPwdActual', 'inputPwdNueva', 'inputPwdConfirmar', 'inputPwdCodigo'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) { el.value = ''; }
        });
        var p1 = document.getElementById('pasoPwd1');
        var p2 = document.getElementById('pasoPwd2');
        if (p1) { p1.style.display = 'block'; }
        if (p2) { p2.style.display = 'none'; }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var btnEditarTel = document.getElementById('btnEditarTelefono');
        if (btnEditarTel) { btnEditarTel.addEventListener('click', function () { mostrarEdicionTelefono(true); }); }

        var btnCancelarTel = document.getElementById('btnCancelarTelefono');
        if (btnCancelarTel) { btnCancelarTel.addEventListener('click', cancelarEdicionTelefono); }

        var btnTel = document.getElementById('btnGuardarTelefono');
        if (btnTel) { btnTel.addEventListener('click', guardarTelefono); }

        var inputTel = document.getElementById('inputTelefono');
        if (inputTel) {
            inputTel.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') { e.preventDefault(); guardarTelefono(); }
                else if (e.key === 'Escape') { cancelarEdicionTelefono(); }
            });
        }

        var btnEnviar = document.getElementById('btnEnviarCodigoPwd');
        if (btnEnviar) { btnEnviar.addEventListener('click', solicitarCodigo); }

        var btnReenviar = document.getElementById('btnReenviarCodigoPwd');
        if (btnReenviar) { btnReenviar.addEventListener('click', solicitarCodigo); }

        var btnConfirmar = document.getElementById('btnConfirmarCodigoPwd');
        if (btnConfirmar) { btnConfirmar.addEventListener('click', confirmarCodigo); }

        // Código: solo dígitos y autoconfirmación al completar los 6.
        var inputCodigo = document.getElementById('inputPwdCodigo');
        if (inputCodigo) {
            inputCodigo.addEventListener('input', function () {
                this.value = this.value.replace(/\D/g, '').slice(0, 6);
                if (this.value.length === 6) { confirmarCodigo(); }
            });
        }

        var btnVolver = document.getElementById('btnVolverPwd1');
        if (btnVolver) { btnVolver.addEventListener('click', reiniciarFormularioPwd); }
    });
})();
