// =============================================
// MODO OSCURO - GLOBAL
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

document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('modoOscuro') === 'true') {
        document.body.classList.add('modo-oscuro');
        var checkbox = document.getElementById('modoOscuro');
        if (checkbox) checkbox.checked = true;
    }
});