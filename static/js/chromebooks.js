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
                
                var estadoClass = d.estado === 'disponible' ? 'success' : (d.estado === 'prestado' ? 'warning' : 'danger');
                document.getElementById('detalleEstadoBadge').innerHTML = '<span class="badge bg-' + estadoClass + ' px-3 py-2">' + d.estado.toUpperCase() + '</span>';
                
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
                document.getElementById('editId').value = id;
                document.getElementById('editCodigo').value = data.data.codigo;
                document.getElementById('editMarca').value = data.data.marca;
                document.getElementById('editModelo').value = data.data.modelo;
                document.getElementById('editSerie').value = data.data.serie;
                document.getElementById('editEstado').value = data.data.estado;
                document.getElementById('editCondicion').value = data.data.condicion;
                document.getElementById('editNotas').value = data.data.notas || '';
                
                var modal = new bootstrap.Modal(document.getElementById('modalEditarChromebook'));
                modal.show();
            }
        });
}

function guardarEdicion() {
    var id = document.getElementById('editId').value;
    var data = {
        marca: document.getElementById('editMarca').value,
        modelo: document.getElementById('editModelo').value,
        serie: document.getElementById('editSerie').value,
        estado: document.getElementById('editEstado').value,
        condicion: document.getElementById('editCondicion').value,
        notas: document.getElementById('editNotas').value
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

function getCSRFToken() {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.startsWith('csrftoken=')) return c.substring('csrftoken='.length);
    }
    return '';
}