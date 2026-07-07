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
    var sel = document.getElementById('editRol');
    sel.value = rolActual;
    sel.dispatchEvent(new Event('cs:refresh'));  // refresca el select animado
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

// Abre el modal de confirmación de eliminación de un técnico de TICs
function abrirEliminarTecnico(tecnicoId, nombre, enProceso) {
    document.getElementById('delTecnicoId').value = tecnicoId;
    document.getElementById('delTecnicoNombre').textContent = nombre;
    var texto = document.getElementById('delTecnicoTexto');
    if (enProceso > 0) {
        texto.innerHTML = '<strong>' + nombre + '</strong> tiene ' + enProceso +
            ' equipo(s) en mantenimiento. Debes finalizar o reasignar esos trabajos antes de eliminarlo.';
    } else {
        texto.innerHTML = '¿Seguro que deseas eliminar a <strong>' + nombre + '</strong>? Esta acción no se puede deshacer.';
    }
    abrirModal('modalEliminarTecnico');
}

// Abre el modal de edición de un técnico, precargado con sus datos.
function abrirEditarTecnico(id, nombres, apellidos, cedula, telefono, correo, especialidad) {
    document.getElementById('etecId').value = id;
    document.getElementById('etecNombres').value = nombres || '';
    document.getElementById('etecApellidos').value = apellidos || '';
    document.getElementById('etecCedula').value = cedula || '';
    document.getElementById('etecTelefono').value = telefono || '';
    document.getElementById('etecCorreo').value = correo || '';
    document.getElementById('etecEspecialidad').value = especialidad || '';
    abrirModal('modalEditarTecnico');
}
