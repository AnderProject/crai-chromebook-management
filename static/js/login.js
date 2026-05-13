// static/js/login.js

document.addEventListener('DOMContentLoaded', function() {
    
    // =============================================
    // MOSTRAR/OCULTAR CONTRASEÑA
    // =============================================
    const btnMostrarContraseña = document.getElementById('btnMostrarContraseña');
    const campoContraseña = document.getElementById('id_contraseña');
    
    if (btnMostrarContraseña && campoContraseña) {
        btnMostrarContraseña.addEventListener('click', function() {
            const tipo = campoContraseña.getAttribute('type') === 'password' ? 'text' : 'password';
            campoContraseña.setAttribute('type', tipo);
            
            const icono = this.querySelector('i');
            if (tipo === 'text') {
                icono.classList.remove('bi-eye-fill');
                icono.classList.add('bi-eye-slash-fill');
            } else {
                icono.classList.remove('bi-eye-slash-fill');
                icono.classList.add('bi-eye-fill');
            }
            
            campoContraseña.focus();
        });
    }
    
    // =============================================
    // VALIDACIÓN DEL FORMULARIO
    // =============================================
    const formularioLogin = document.getElementById('formularioLogin');
    
    if (formularioLogin) {
        formularioLogin.addEventListener('submit', function(evento) {
            let esValido = true;
            limpiarErrores();
            
            const usuario = document.getElementById('id_usuario');
            if (!usuario.value.trim()) {
                mostrarError('error_usuario', '✖ El usuario es requerido');
                usuario.classList.add('is-invalid');
                esValido = false;
            }
            
            const contraseña = document.getElementById('id_contraseña');
            if (!contraseña.value) {
                mostrarError('error_contraseña', '✖ La contraseña es requerida');
                contraseña.classList.add('is-invalid');
                esValido = false;
            }
            
            if (!esValido) {
                evento.preventDefault();
                formularioLogin.classList.add('shake');
                setTimeout(() => {
                    formularioLogin.classList.remove('shake');
                }, 600);
            }
        });
    }
    
    // =============================================
    // FUNCIONES AUXILIARES
    // =============================================
    function mostrarError(idElemento, mensaje) {
        const elemento = document.getElementById(idElemento);
        if (elemento) {
            elemento.textContent = mensaje;
        }
    }
    
    function limpiarErrores() {
        document.querySelectorAll('.form-control').forEach(campo => {
            campo.classList.remove('is-invalid');
        });
        document.querySelectorAll('.form-text').forEach(error => {
            error.textContent = '';
        });
    }
});