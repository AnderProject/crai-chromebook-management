// =============================================
// LOADER DE CARGA - CRAI UNEMI
// Overlay transparente y borroso: aparece en cada carga y en procesos manuales
// =============================================

// Mostrar el loader manualmente (procesos / actualizaciones)
function mostrarLoader() {
    var loader = document.getElementById('craiLoader');
    if (loader) loader.classList.remove('oculto');
}

// Ocultar el loader
function ocultarLoader() {
    var loader = document.getElementById('craiLoader');
    if (loader) loader.classList.add('oculto');
}

document.addEventListener('DOMContentLoaded', function () {
    var loader = document.getElementById('craiLoader');
    if (loader) {
        setTimeout(ocultarLoader, 1100);
    }
});
