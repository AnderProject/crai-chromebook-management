// =============================================
// AJUSTES - CRAI UNEMI
// Modo oscuro y preferencias
// =============================================

function toggleModoOscuro() {
    var activo = document.getElementById('modoOscuro').checked;
    
    if (activo) {
        document.body.classList.add('modo-oscuro');
        localStorage.setItem('modoOscuro', 'true');
    } else {
        document.body.classList.remove('modo-oscuro');
        localStorage.setItem('modoOscuro', 'false');
    }
}

// Cargar preferencia al iniciar
document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('modoOscuro') === 'true') {
        document.getElementById('modoOscuro').checked = true;
        document.body.classList.add('modo-oscuro');
    }
});