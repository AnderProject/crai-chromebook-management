var chromebookSeleccionado = null;
var estudianteSeleccionado = null;
var duracionSeleccionada = 4;

document.addEventListener('DOMContentLoaded', function() {
    
    // Selector de tiempo
    document.querySelectorAll('.tiempo-chip').forEach(function(chip) {
        chip.addEventListener('click', function() {
            document.querySelectorAll('.tiempo-chip').forEach(function(c) { c.classList.remove('activo'); });
            this.classList.add('activo');
            duracionSeleccionada = parseInt(this.getAttribute('data-tiempo'));
        });
    });
    
    // Buscar Chromebook
    document.getElementById('btnBuscarChromebook').addEventListener('click', function() {
        var codigo = document.getElementById('codigoChromebook').value.trim();
        if (!codigo) return;
        
        fetch('/prestamos/api/buscar-chromebook/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify({ codigo: codigo })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var div = document.getElementById('infoChromebook');
            if (data.success) {
                chromebookSeleccionado = data.data;
                div.innerHTML = '<span class="text-success"><i class="bi bi-check-circle me-1"></i>' + data.data.codigo + ' • ' + data.data.marca + ' ' + data.data.modelo + ' • <strong>' + data.data.estado + '</strong></span>';
            } else {
                chromebookSeleccionado = null;
                div.innerHTML = '<span class="text-danger"><i class="bi bi-x-circle me-1"></i>' + data.message + '</span>';
            }
        });
    });
    
    // Buscar Estudiante
    document.getElementById('btnBuscarEstudiante').addEventListener('click', function() {
        var cedula = document.getElementById('cedulaEstudiante').value.trim();
        if (!cedula) return;
        
        fetch('/prestamos/api/buscar-estudiante/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify({ cedula: cedula })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var div = document.getElementById('infoEstudiante');
            if (data.success) {
                estudianteSeleccionado = data.data;
                div.innerHTML = '<span class="text-info"><i class="bi bi-person-check me-1"></i>' + data.data.nombre + ' • ' + data.data.carrera + '</span>';
            } else {
                estudianteSeleccionado = null;
                div.innerHTML = '<span class="text-danger"><i class="bi bi-person-x me-1"></i>' + data.message + '</span>';
            }
        });
    });
    
    // Registrar préstamo
    document.getElementById('btnPrestarAhora').addEventListener('click', function() {
        if (!chromebookSeleccionado) { alert('Busca un Chromebook primero.'); return; }
        if (!estudianteSeleccionado) { alert('Busca un estudiante primero.'); return; }
        if (chromebookSeleccionado.estado !== 'disponible') { alert('El Chromebook no está disponible.'); return; }
        
        if (confirm('¿Confirmar préstamo de ' + chromebookSeleccionado.codigo + ' a ' + estudianteSeleccionado.nombre + ' por ' + duracionSeleccionada + ' horas?')) {
            fetch('/prestamos/api/registrar-prestamo/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
                body: JSON.stringify({
                    chromebook_id: chromebookSeleccionado.id,
                    user_id: estudianteSeleccionado.user_id,
                    duracion: duracionSeleccionada
                })
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    alert('✅ ' + data.message);
                    location.reload();
                } else {
                    alert('❌ ' + data.message);
                }
            });
        }
    });
    
});

function getCSRFToken() {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.startsWith('csrftoken=')) return c.substring('csrftoken='.length);
    }
    return '';
}