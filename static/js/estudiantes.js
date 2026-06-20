function cambiarTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
    
    if (tab === 'directorio') {
        document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
    } else {
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
    }
    
    document.getElementById('tab-directorio').style.display = tab === 'directorio' ? 'block' : 'none';
    document.getElementById('tab-monitoreo').style.display = tab === 'monitoreo' ? 'block' : 'none';
}

function filtrarEstudiantes() {
    var busqueda = document.getElementById('buscarEstudiante').value.toLowerCase();
    var carrera = document.getElementById('filtroCarrera').value.toLowerCase();
    
    document.querySelectorAll('.estudiante-row').forEach(function(row) {
        var nombre = row.getAttribute('data-nombre') || '';
        var cedula = row.getAttribute('data-cedula') || '';
        var carreraRow = row.getAttribute('data-carrera') || '';
        
        var coincideBusqueda = nombre.includes(busqueda) || cedula.includes(busqueda);
        var coincideCarrera = !carrera || carreraRow.includes(carrera);
        
        row.style.display = (coincideBusqueda && coincideCarrera) ? 'flex' : 'none';
    });
}

function abrirPerfil(id) {
    console.log('Abriendo perfil del estudiante ID:', id);
    
    fetch('/prestamos/api/perfil-estudiante/' + id + '/')
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Error en la respuesta');
            }
            return response.json();
        })
        .then(function(data) {
            document.getElementById('perfilAvatar').textContent = data.avatar || '-';
            document.getElementById('perfilNombre').textContent = data.nombre || '-';
            document.getElementById('perfilCedula').textContent = data.cedula || '-';
            document.getElementById('perfilCarrera').textContent = data.carrera || '-';
            document.getElementById('perfilSemestre').textContent = (data.semestre || '') + 'to Semestre';
            document.getElementById('perfilEmail').textContent = data.email || '-';

            renderResumen(data.resumen || {});
            renderHistorial(data.historial || []);

            document.getElementById('modalPerfil').classList.add('abierto');
            document.getElementById('overlay').classList.add('visible');
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('Error al cargar el perfil del estudiante');
        });
}

function renderResumen(r) {
    var html =
        '<div class="perfil-resumen-card"><div class="perfil-resumen-num text-primary">' + (r.total || 0) + '</div><span class="perfil-resumen-lbl">Préstamos</span></div>' +
        '<div class="perfil-resumen-card"><div class="perfil-resumen-num text-warning">' + (r.activos || 0) + '</div><span class="perfil-resumen-lbl">Activos</span></div>' +
        '<div class="perfil-resumen-card"><div class="perfil-resumen-num text-danger">' + (r.vencidos || 0) + '</div><span class="perfil-resumen-lbl">Vencidos</span></div>';
    document.getElementById('perfilResumen').innerHTML = html;
}

function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
}

function renderHistorial(historial) {
    var cont = document.getElementById('perfilHistorial');
    if (!historial.length) {
        cont.innerHTML = '<div class="historial-vacio"><i class="bi bi-inbox d-block mb-1" style="font-size:1.5rem;"></i>Sin historial de préstamos</div>';
        return;
    }

    var estadoClase = { 'devuelto': 'estado-devuelto', 'activo': 'estado-activo', 'vencido': 'estado-vencido' };
    var html = '';
    historial.forEach(function(h) {
        var clase = estadoClase[h.estado] || '';
        var codigo = escapeHtml(h.codigo);

        var foto;
        if (h.foto_url) {
            var etiqueta = h.foto_tipo === 'devolucion' ? 'Devolución' : 'Entrega';
            foto = '<img src="' + encodeURI(h.foto_url) + '" class="historial-foto" alt="Evidencia" ' +
                   'onclick="verFotoEvidencia(\'' + encodeURI(h.foto_url) + '\', \'' + etiqueta + ' · ' + codigo + '\')">';
        } else {
            foto = '<div class="historial-foto-vacia"><i class="bi bi-camera"></i></div>';
        }

        var meta = '<i class="bi bi-calendar3"></i> ' + escapeHtml(h.fecha) + ' · ' + (h.duracion || 0) + 'h';
        if (h.fecha_devuelto) {
            meta += '<br><i class="bi bi-arrow-return-left"></i> Devuelto: ' + escapeHtml(h.fecha_devuelto);
        }

        html +=
            '<div class="historial-card ' + clase + '">' +
                foto +
                '<div class="historial-info">' +
                    '<div class="d-flex justify-content-between align-items-center mb-1">' +
                        '<span class="historial-codigo">' + codigo + '</span>' +
                        '<span class="historial-badge ' + clase + '">' + escapeHtml(h.estado) + '</span>' +
                    '</div>' +
                    '<div class="historial-meta">' + meta + '</div>' +
                '</div>' +
            '</div>';
    });
    cont.innerHTML = html;
}

function verFotoEvidencia(url, titulo) {
    document.getElementById('fotoEvidenciaImg').src = url;
    document.getElementById('fotoEvidenciaTitulo').textContent = titulo || 'Evidencia';
    new bootstrap.Modal(document.getElementById('modalFotoEvidencia')).show();
}

function cerrarPerfil() {
    document.getElementById('modalPerfil').classList.remove('abierto');
    document.getElementById('overlay').classList.remove('visible');
}