// =============================================
// Portal del estudiante · CRAI UNEMI
// Modal de soporte (abrir/cerrar + tecla Escape)
// =============================================
function abrirModalSoporte() {
    var m = document.getElementById('soporteModal');
    if (m) m.classList.add('visible');
}

function cerrarModalSoporte() {
    var m = document.getElementById('soporteModal');
    if (m) m.classList.remove('visible');
}

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') cerrarModalSoporte();
});
