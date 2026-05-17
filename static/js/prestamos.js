// =============================================
// REGISTRO RÁPIDO DE PRÉSTAMOS - CRAI UNEMI
// =============================================

document.addEventListener('DOMContentLoaded', function() {
    
    // Selector de tiempo (chips)
    document.querySelectorAll('.tiempo-chip').forEach(function(chip) {
        chip.addEventListener('click', function() {
            document.querySelectorAll('.tiempo-chip').forEach(function(c) {
                c.classList.remove('activo');
            });
            this.classList.add('activo');
        });
    });
    
    // Buscar Chromebook
    document.getElementById('btnBuscarChromebook').addEventListener('click', function() {
        var codigo = document.getElementById('codigoChromebook').value;
        var div = document.getElementById('infoChromebook');
        
        if (codigo === '015') {
            div.innerHTML = '<span class="text-success"><i class="bi bi-check-circle me-1"></i>CB-015 • HP 11 G8 • <strong>Disponible</strong></span>';
        } else if (codigo) {
            div.innerHTML = '<span class="text-danger"><i class="bi bi-x-circle me-1"></i>No encontrado</span>';
        }
    });
    
    // Buscar Estudiante
    document.getElementById('btnBuscarEstudiante').addEventListener('click', function() {
        var cedula = document.getElementById('cedulaEstudiante').value;
        var div = document.getElementById('infoEstudiante');
        
        if (cedula === '0923456789') {
            div.innerHTML = '<span class="text-info"><i class="bi bi-person-check me-1"></i>Anderson Merchán • Ing. Software</span>';
        } else if (cedula) {
            div.innerHTML = '<span class="text-warning"><i class="bi bi-person-x me-1"></i>No encontrado</span>';
        }
    });
    
    // Registrar préstamo
    document.getElementById('btnPrestarAhora').addEventListener('click', function() {
        var codigo = document.getElementById('codigoChromebook').value;
        var cedula = document.getElementById('cedulaEstudiante').value;
        
        if (!codigo || !cedula) {
            alert('Complete los campos requeridos');
            return;
        }
        
        if (confirm('¿Confirmar préstamo?')) {
            alert('✅ Préstamo registrado');
            document.getElementById('codigoChromebook').value = '';
            document.getElementById('cedulaEstudiante').value = '';
            document.getElementById('infoChromebook').innerHTML = '';
            document.getElementById('infoEstudiante').innerHTML = '';
        }
    });
    
});