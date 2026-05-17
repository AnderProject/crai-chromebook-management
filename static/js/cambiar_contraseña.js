// =============================================
// CAMBIAR CONTRASEÑA - CRAI UNEMI
// Mostrar / Ocultar contraseña
// =============================================

document.addEventListener('DOMContentLoaded', function() {
    const btnMostrar = document.getElementById('btnMostrarContraseña');
    const campo = document.getElementById('nueva_contraseña');
    
    if (btnMostrar && campo) {
        btnMostrar.addEventListener('click', function() {
            // Cambiar tipo de input
            const tipo = campo.getAttribute('type') === 'password' ? 'text' : 'password';
            campo.setAttribute('type', tipo);
            
            // Cambiar ícono
            const icono = this.querySelector('i');
            if (tipo === 'text') {
                icono.classList.replace('bi-eye-fill', 'bi-eye-slash-fill');
            } else {
                icono.classList.replace('bi-eye-slash-fill', 'bi-eye-fill');
            }
        });
    }
});