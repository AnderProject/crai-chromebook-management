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
            console.log('Datos recibidos:', data);
            
            document.getElementById('perfilAvatar').textContent = data.avatar || '-';
            document.getElementById('perfilNombre').textContent = data.nombre || '-';
            document.getElementById('perfilCedula').textContent = data.cedula || '-';
            document.getElementById('perfilCarrera').textContent = data.carrera || '-';
            document.getElementById('perfilSemestre').textContent = (data.semestre || '') + 'to';
            document.getElementById('perfilEmail').textContent = data.email || '-';
            document.getElementById('perfilHistorial').innerHTML = data.historial || 'Sin historial';
            
            document.getElementById('modalPerfil').classList.add('abierto');
            document.getElementById('overlay').classList.add('visible');
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('Error al cargar el perfil del estudiante');
        });
}

function cerrarPerfil() {
    document.getElementById('modalPerfil').classList.remove('abierto');
    document.getElementById('overlay').classList.remove('visible');
}