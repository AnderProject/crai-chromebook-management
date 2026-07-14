function filtrarChromebooks() {
    var busqueda = document.getElementById('buscarChromebook').value.toLowerCase().trim();
    var estado = document.getElementById('filtroEstado').value.toLowerCase();
    var marca = document.getElementById('filtroMarca').value.toLowerCase();
    
    var filas = document.querySelectorAll('.tabla-prestamos tbody tr');
    var visibles = 0;
    
    filas.forEach(function(fila) {
        var codigo = fila.getAttribute('data-codigo') || '';
        var marcaRow = fila.getAttribute('data-marca') || '';
        var modelo = fila.getAttribute('data-modelo') || '';
        var estadoRow = fila.getAttribute('data-estado') || '';
        
        var coincideBusqueda = !busqueda || codigo.includes(busqueda) || marcaRow.includes(busqueda) || modelo.includes(busqueda);
        var coincideEstado = !estado || estadoRow === estado;
        var coincideMarca = !marca || marcaRow === marca;
        
        if (coincideBusqueda && coincideEstado && coincideMarca) {
            fila.style.display = '';
            visibles++;
        } else {
            fila.style.display = 'none';
        }
    });
}





// =============================================
// VER DETALLE DE CHROMEBOOK
// =============================================
function verDetalleChromebook(id) {
    fetch('/prestamos/api/detalle-chromebook/' + id + '/')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                var d = data.data;
                
                // Si tiene foto, usar la foto real. Si no, mostrar placeholder
                var imgSrc = d.foto_url || 'https://cdn-icons-png.flaticon.com/512/2983/2983063.png';
                
                document.getElementById('detalleTitulo').textContent = d.marca + ' Chromebook';
                document.getElementById('detalleImagen').src = imgSrc;
                document.getElementById('detalleCodigoImg').textContent = d.codigo;
                document.getElementById('detalleMarcaModelo').textContent = d.marca + ' ' + d.modelo;
                
                // Badge por el estado EFECTIVO (considera reservas pendientes).
                var ef = d.estado_efectivo || d.estado;
                var badges = {
                    disponible: ['success', 'Disponible'],
                    pendiente_reserva: ['pendiente', 'Pendiente a reserva'],
                    prestado: ['warning', 'Prestado'],
                    reservado: ['pendiente', 'Reservado'],
                    mantenimiento: ['danger', 'Mantenimiento']
                };
                var b = badges[ef] || ['secondary', ef];
                document.getElementById('detalleEstadoBadge').innerHTML = '<span class="badge bg-' + b[0] + ' px-3 py-2">' + b[1] + '</span>';

                // Banner de conexión del kiosko
                var conexion = document.getElementById('detalleConexion');
                if (conexion) {
                    if (d.en_linea) {
                        conexion.className = 'cb-conexion-banner en-linea mt-3';
                        conexion.innerHTML = '<span class="cb-conexion-dot"></span>' +
                            '<span><i class="bi bi-wifi me-1"></i>Equipo en línea</span>';
                    } else {
                        conexion.className = 'cb-conexion-banner desconectado mt-3';
                        conexion.innerHTML = '<span class="cb-conexion-dot"></span>' +
                            '<span><i class="bi bi-wifi-off me-1"></i>Desconectado · ' + (d.ultima_conexion || 'Nunca') + '</span>';
                    }
                }

                var modal = new bootstrap.Modal(document.getElementById('modalDetalleChromebook'));
                modal.show();
            }
        });
}



// =============================================
// EDITAR CHROMEBOOK
// =============================================
function editarChromebook(id) {
    fetch('/prestamos/api/detalle-chromebook/' + id + '/')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                var d = data.data;
                document.getElementById('editId').value = id;
                document.getElementById('editCodigo').value = d.codigo;
                // Marca: si la del equipo no está en la lista, se inyecta para poder mostrarla.
                var selMarca = document.getElementById('editMarca');
                if (d.marca && !selMarca.querySelector('option[value="' + d.marca + '"]')) {
                    var om = document.createElement('option');
                    om.value = d.marca; om.textContent = d.marca;
                    selMarca.appendChild(om);
                }
                selMarca.value = d.marca;
                document.getElementById('editModelo').value = d.modelo;
                document.getElementById('editSerie').value = d.serie;
                // "Mantenimiento" no es una opción asignable; si el equipo ya está en
                // mantenimiento, se inyecta la opción solo para mostrar su estado.
                var selEstado = document.getElementById('editEstado');
                if (d.estado === 'mantenimiento' && !selEstado.querySelector('option[value="mantenimiento"]')) {
                    var opt = document.createElement('option');
                    opt.value = 'mantenimiento';
                    opt.textContent = 'Mantenimiento';
                    selEstado.appendChild(opt);
                }
                selEstado.value = d.estado;
                document.getElementById('editCondicion').value = d.condicion;
                // Refrescar los selects animados con los valores cargados.
                ['editMarca', 'editEstado', 'editCondicion'].forEach(function (sid) {
                    document.getElementById(sid).dispatchEvent(new Event('cs:refresh'));
                });
                document.getElementById('editNotas').value = d.notas || '';

                // Fecha de compra y garantía
                document.getElementById('editFechaAdquisicion').value = d.fecha_adquisicion || '';
                document.getElementById('editTieneGarantia').checked = !!d.tiene_garantia;
                document.getElementById('editFechaFinGarantia').value = d.fecha_fin_garantia || '';
                toggleGarantiaEdit();

                bloquearEstadoMantenimiento(d.estado);

                var modal = new bootstrap.Modal(document.getElementById('modalEditarChromebook'));
                modal.show();
            }
        });
}

// Muestra/oculta la fecha de fin de garantía en el modal de edición
function toggleGarantiaEdit() {
    var tiene = document.getElementById('editTieneGarantia').checked;
    document.getElementById('editWrapFinGarantia').style.display = tiene ? '' : 'none';
    if (!tiene) document.getElementById('editFechaFinGarantia').value = '';
}

// Si el equipo está en mantenimiento, no se puede cambiar a disponible/prestado
// desde el inventario: se bloquea el select y se muestra el aviso. Debe finalizarse
// el mantenimiento desde su sección dedicada.
function bloquearEstadoMantenimiento(estado) {
    var select = document.getElementById('editEstado');
    var aviso = document.getElementById('editMantAviso');
    var enMant = (estado === 'mantenimiento');
    select.disabled = enMant;
    aviso.style.display = enMant ? '' : 'none';
}

function guardarEdicion() {
    var id = document.getElementById('editId').value;
    var data = {
        marca: document.getElementById('editMarca').value,
        modelo: document.getElementById('editModelo').value,
        serie: document.getElementById('editSerie').value,
        estado: document.getElementById('editEstado').value,
        condicion: document.getElementById('editCondicion').value,
        notas: document.getElementById('editNotas').value,
        fecha_adquisicion: document.getElementById('editFechaAdquisicion').value,
        tiene_garantia: document.getElementById('editTieneGarantia').checked,
        fecha_fin_garantia: document.getElementById('editFechaFinGarantia').value
    };

    fetch('/prestamos/api/editar-chromebook/' + id + '/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify(data)
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            mostrarToastTrasReload('Chromebook actualizado', 'success');
            location.reload();
        } else {
            mostrarToast(data.message || 'Error al actualizar', 'error');
        }
    });
}

// ===== ELIMINAR CHROMEBOOK =====
// Abre el modal de confirmación con el código del equipo que se está editando.
function eliminarChromebook() {
    var codigo = document.getElementById('editCodigo').value || 'este equipo';
    document.getElementById('delCbCodigo').textContent = codigo;
    var edit = bootstrap.Modal.getInstance(document.getElementById('modalEditarChromebook'));
    if (edit) edit.hide();
    new bootstrap.Modal(document.getElementById('modalEliminarChromebook')).show();
}

function confirmarEliminarChromebook() {
    var id = document.getElementById('editId').value;
    var btn = document.getElementById('btnConfirmarEliminarCb');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Eliminando...'; }

    fetch('/prestamos/api/eliminar-chromebook/' + id + '/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            mostrarToastTrasReload(data.message || 'Equipo eliminado', 'success');
            location.reload();
        } else {
            var modal = bootstrap.Modal.getInstance(document.getElementById('modalEliminarChromebook'));
            if (modal) modal.hide();
            mostrarToast(data.message || 'No se pudo eliminar', 'error');
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-trash me-1"></i>Sí, eliminar'; }
        }
    })
    .catch(function() {
        mostrarToast('Error de conexión al eliminar.', 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-trash me-1"></i>Sí, eliminar'; }
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