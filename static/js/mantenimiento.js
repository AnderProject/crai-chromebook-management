// =============================================
// BÚSQUEDA POR CÓDIGO DE MÁQUINA
// =============================================
document.addEventListener('DOMContentLoaded', function () {
    var input = document.getElementById('buscarMantenimiento');
    var limpiar = document.getElementById('btnLimpiarBusqueda');
    if (!input) { return; }

    // Búsqueda automática mientras se escribe
    input.addEventListener('input', filtrarMantenimientos);
    if (limpiar) {
        limpiar.addEventListener('click', function () {
            input.value = '';
            filtrarMantenimientos();
            input.focus();
        });
    }
});

function filtrarMantenimientos() {
    var input = document.getElementById('buscarMantenimiento');
    var termino = (input.value || '').trim().toLowerCase();
    var filas = document.querySelectorAll('tbody tr[data-codigo]');
    var visibles = 0;

    filas.forEach(function (fila) {
        var codigo = fila.getAttribute('data-codigo') || '';
        var coincide = !termino || codigo.indexOf(termino) !== -1;
        fila.classList.toggle('d-none', !coincide);
        if (coincide) { visibles++; }
    });

    var sinResultados = document.getElementById('filaSinResultados');
    if (sinResultados) {
        sinResultados.classList.toggle('d-none', !(termino && visibles === 0));
    }
}

// =============================================
// EDICIÓN DE MANTENIMIENTO - CRAI UNEMI
// =============================================

function editarMantenimiento(id) {
    fetch('/prestamos/api/detalle-mantenimiento/' + id + '/')
        .then(function (r) { return r.json(); })
        .then(function (resp) {
            if (!resp.success) {
                mostrarToast(resp.message || 'No se pudo cargar el mantenimiento', 'error');
                return;
            }
            var d = resp.data;
            document.getElementById('editMantId').value = d.id;
            document.getElementById('editMantChromebook').value = d.chromebook;
            document.getElementById('editMantTipo').value = d.tipo;
            document.getElementById('editMantTecnico').value = d.tecnico;
            document.getElementById('editMantCosto').value = d.costo;
            document.getElementById('editMantGarantia').value = d.en_garantia ? '1' : '0';
            document.getElementById('editMantFechaInicio').value = d.fecha_inicio;
            document.getElementById('editMantProblema').value = d.descripcion_problema;

            var modal = new bootstrap.Modal(document.getElementById('modalEditarMantenimiento'));
            modal.show();
        });
}

function guardarEdicionMantenimiento() {
    var id = document.getElementById('editMantId').value;
    var data = {
        tipo: document.getElementById('editMantTipo').value,
        tecnico: document.getElementById('editMantTecnico').value,
        costo: document.getElementById('editMantCosto').value,
        en_garantia: document.getElementById('editMantGarantia').value === '1',
        fecha_inicio: document.getElementById('editMantFechaInicio').value,
        descripcion_problema: document.getElementById('editMantProblema').value
    };

    fetch('/prestamos/api/editar-mantenimiento/' + id + '/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify(data)
    })
        .then(function (r) { return r.json(); })
        .then(function (resp) {
            if (resp.success) {
                mostrarToastTrasReload('Mantenimiento actualizado', 'success');
                location.reload();
            } else {
                mostrarToast(resp.message || 'Error al actualizar', 'error');
            }
        });
}

function getCSRFToken() {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.startsWith('csrftoken=')) return c.substring('csrftoken='.length);
    }
    return '';
}
