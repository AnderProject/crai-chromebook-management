// =============================================
// LOADER DE CARGA - CRAI UNEMI
// Controla la animación de carga
// =============================================

document.addEventListener('DOMContentLoaded', function() {
    
    var loader = document.getElementById('craiLoader');
    
    // Ocultar el loader después de 2 segundos
    if (loader) {
        setTimeout(function() {
            loader.classList.add('oculto');
        }, 2000);
    }
    
});

// Función para mostrar el loader manualmente (al hacer clic en botones)
function mostrarLoader() {
    var loader = document.getElementById('craiLoader');
    if (loader) {
        loader.classList.remove('oculto');
        loader.style.opacity = '1';
        loader.style.visibility = 'visible';
    }
}

// Función para ocultar el loader
function ocultarLoader() {
    var loader = document.getElementById('craiLoader');
    if (loader) {
        loader.classList.add('oculto');
    }
}