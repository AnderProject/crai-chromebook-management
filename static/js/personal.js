// =============================================
// GESTIÓN DE PERSONAL (admin) - CRAI UNEMI
// =============================================

function abrirModal(id) {
    var m = document.getElementById(id);
    if (m) m.classList.add('visible');
}

function cerrarModal(id) {
    var m = document.getElementById(id);
    if (m) m.classList.remove('visible');
}

// Abre el modal de cambio de rol precargado con los datos de la persona
function abrirEditarRol(userId, nombre, rolActual) {
    document.getElementById('editUserId').value = userId;
    document.getElementById('editNombre').textContent = nombre;
    document.getElementById('editRol').value = rolActual;
    abrirModal('modalEditarRol');
}

// Abre el modal de confirmación de eliminación
function abrirEliminar(userId, nombre) {
    document.getElementById('delUserId').value = userId;
    document.getElementById('delNombre').textContent = nombre;
    abrirModal('modalEliminar');
}

// Cerrar al hacer clic en el fondo oscuro o con la tecla Escape
document.addEventListener('click', function (e) {
    if (e.target.classList && e.target.classList.contains('modal-personal')) {
        e.target.classList.remove('visible');
    }
});

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-personal.visible').forEach(function (m) {
            m.classList.remove('visible');
        });
    }
});
