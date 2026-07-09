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

function filtrarMonitoreo() {
    var busqueda = document.getElementById('buscarMonitoreo').value.toLowerCase().trim();

    document.querySelectorAll('.monitoreo-lista').forEach(function(lista) {
        var cards = lista.querySelectorAll('.monitoreo-card');
        var visibles = 0;
        cards.forEach(function(card) {
            var texto = card.getAttribute('data-buscar') || '';
            var mostrar = !busqueda || texto.indexOf(busqueda) !== -1;
            card.style.display = mostrar ? '' : 'none';
            if (mostrar) visibles++;
        });
        // "Sin coincidencias" solo cuando hay tarjetas pero ninguna coincide con la búsqueda.
        var sinCoincidencias = lista.querySelector('.monitoreo-sin-coincidencias');
        if (sinCoincidencias) {
            sinCoincidencias.style.display = (busqueda && cards.length > 0 && visibles === 0) ? 'block' : 'none';
        }
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
            var avatarEl = document.getElementById('perfilAvatar');
            if (data.foto_url) {
                avatarEl.innerHTML = '<img src="' + encodeURI(data.foto_url) + '" alt="Foto" class="avatar-img">';
            } else {
                avatarEl.textContent = data.avatar || '-';
            }
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
        '<button type="button" class="perfil-resumen-card filtro-historial activo" data-filtro="total" onclick="filtrarHistorial(\'total\', this)">' +
            '<div class="perfil-resumen-num n-total">' + (r.total || 0) + '</div><span class="perfil-resumen-lbl">Registros</span></button>' +
        '<button type="button" class="perfil-resumen-card filtro-historial" data-filtro="activos" onclick="filtrarHistorial(\'activos\', this)">' +
            '<div class="perfil-resumen-num text-warning">' + (r.activos || 0) + '</div><span class="perfil-resumen-lbl">Activos</span></button>' +
        '<button type="button" class="perfil-resumen-card filtro-historial" data-filtro="vencidos" onclick="filtrarHistorial(\'vencidos\', this)">' +
            '<div class="perfil-resumen-num text-danger">' + (r.vencidos || 0) + '</div><span class="perfil-resumen-lbl">Vencidos</span></button>' +
        '<button type="button" class="perfil-resumen-card filtro-historial" data-filtro="cancelados" onclick="filtrarHistorial(\'cancelados\', this)">' +
            '<div class="perfil-resumen-num n-cancel">' + (r.cancelados || 0) + '</div><span class="perfil-resumen-lbl">Cancelados</span></button>';
    document.getElementById('perfilResumen').innerHTML = html;
}

function filtrarHistorial(filtro, btn) {
    document.querySelectorAll('#perfilResumen .filtro-historial').forEach(function(b) { b.classList.remove('activo'); });
    if (btn) btn.classList.add('activo');

    var cont = document.getElementById('perfilHistorial');
    var cards = cont.querySelectorAll('.historial-card');
    var visibles = 0;
    cards.forEach(function(c) {
        var cat = c.getAttribute('data-cat');
        var mostrar = filtro === 'total' ||
            (filtro === 'activos' && cat === 'activo') ||
            (filtro === 'vencidos' && cat === 'vencido') ||
            (filtro === 'cancelados' && cat === 'cancelado');
        c.style.display = mostrar ? '' : 'none';
        if (mostrar) visibles++;
    });

    var vacio = document.getElementById('perfilHistorialVacioFiltro');
    if (vacio) {
        var etiquetas = { activos: 'activos', vencidos: 'vencimientos', cancelados: 'cancelaciones' };
        vacio.style.display = (cards.length > 0 && visibles === 0) ? 'block' : 'none';
        vacio.textContent = 'Sin ' + (etiquetas[filtro] || 'registros') + ' para este estudiante';
    }
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

    var estadoClase = {
        'devuelto': 'estado-devuelto', 'activo': 'estado-activo', 'vencido': 'estado-vencido',
        'vencida': 'estado-vencido', 'pendiente': 'estado-pendiente',
        'confirmada': 'estado-activo', 'completada': 'estado-devuelto', 'cancelada': 'estado-cancelada'
    };
    var html = '';
    historial.forEach(function(h) {
        var clase = estadoClase[h.estado] || '';
        var esReserva = h.tipo === 'reserva';
        var codigo = escapeHtml(esReserva ? 'Reserva' : h.codigo);

        // Categoría usada por los filtros del resumen (Total / Activos / Vencidos / Cancelados).
        var cat = 'otros';
        if (h.estado === 'activo') cat = 'activo';
        else if (h.estado === 'vencido' || h.estado === 'vencida') cat = 'vencido';
        else if (h.estado === 'cancelada') cat = 'cancelado';

        var tipoTag = esReserva
            ? '<span class="historial-tipo-tag"><i class="bi bi-calendar-event"></i> Reserva</span>'
            : '<span class="historial-tipo-tag historial-tipo-prestamo"><i class="bi bi-laptop"></i> Préstamo</span>';

        var meta = '<i class="bi bi-calendar3"></i> ' + escapeHtml(h.fecha) + ' · ' + (h.duracion || 0) + 'h';
        if (h.fecha_devuelto) {
            meta += '<br><i class="bi bi-arrow-return-left"></i> Devuelto: ' + escapeHtml(h.fecha_devuelto);
        }

        var infoBlock =
            '<div class="historial-info">' +
                '<div class="d-flex justify-content-between align-items-center mb-1">' +
                    '<span class="historial-codigo">' + codigo + '</span>' +
                    '<span class="historial-badge ' + clase + '">' + escapeHtml(h.estado) + '</span>' +
                '</div>' +
                '<div class="historial-meta">' + tipoTag + ' · ' + meta + '</div>' +
            '</div>';

        if (!esReserva && h.foto_url) {
            // Con evidencia: ícono que despliega la foto EN LÍNEA debajo de la información.
            var etiqueta = h.foto_tipo === 'devolucion' ? 'Devolución' : 'Entrega';
            html +=
                '<div class="historial-card ' + clase + ' con-evidencia" data-cat="' + cat + '">' +
                    '<div class="historial-fila">' +
                        '<button type="button" class="historial-foto-btn" onclick="toggleEvidencia(this)" title="Ver evidencia">' +
                            '<i class="bi bi-image"></i><span class="foto-lupa"><i class="bi bi-arrows-angle-expand"></i></span>' +
                        '</button>' +
                        infoBlock +
                    '</div>' +
                    '<div class="historial-evidencia"><div class="historial-evidencia-inner">' +
                        '<div class="historial-evidencia-cap"><i class="bi bi-camera-fill"></i> Evidencia · ' + etiqueta + '</div>' +
                        '<img src="' + encodeURI(h.foto_url) + '" class="historial-evidencia-img" alt="Evidencia" loading="lazy">' +
                    '</div></div>' +
                '</div>';
        } else {
            // Sin evidencia (o reserva): ícono estático a la izquierda.
            var fotoVacia = esReserva
                ? '<div class="historial-foto-vacia"><i class="bi bi-calendar-check"></i></div>'
                : '<div class="historial-foto-vacia"><i class="bi bi-camera"></i></div>';
            html +=
                '<div class="historial-card ' + clase + '" data-cat="' + cat + '">' +
                    fotoVacia + infoBlock +
                '</div>';
        }
    });
    html += '<div id="perfilHistorialVacioFiltro" class="historial-vacio" style="display:none;"></div>';
    cont.innerHTML = html;
}

// Despliega/oculta la evidencia EN LÍNEA, debajo de la información (sin modal flotante).
function toggleEvidencia(btn) {
    var card = btn.closest('.historial-card');
    if (!card) { return; }
    var panel = card.querySelector('.historial-evidencia');
    if (!panel) { return; }
    var abierto = panel.classList.toggle('abierta');
    btn.classList.toggle('abierta', abierto);
}

function cerrarPerfil() {
    document.getElementById('modalPerfil').classList.remove('abierto');
    document.getElementById('overlay').classList.remove('visible');
}