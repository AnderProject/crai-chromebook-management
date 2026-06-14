// =============================================
// DEVOLUCIÓN DE PRÉSTAMO - CRAI UNEMI
// =============================================

var prestamoADevolver = null;

function confirmarDevolucion(prestamoId, codigo) {
    prestamoADevolver = prestamoId;
    document.getElementById('devolucionMensaje').textContent = 'El equipo ' + codigo + ' será liberado y estará disponible nuevamente.';
    var modal = new bootstrap.Modal(document.getElementById('modalDevolucion'));
    modal.show();
}

document.addEventListener('DOMContentLoaded', function() {
    var btnConfirmar = document.getElementById('btnConfirmarDevolucion');
    if (btnConfirmar) {
        btnConfirmar.addEventListener('click', function() {
            if (!prestamoADevolver) return;
            
            bootstrap.Modal.getInstance(document.getElementById('modalDevolucion')).hide();
            
            fetch('/prestamos/api/devolver-prestamo/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ prestamo_id: prestamoADevolver })
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var icono = document.getElementById('devolucionIcono');
                var titulo = document.getElementById('devolucionTitulo');
                var texto = document.getElementById('devolucionTexto');
                
                if (data.success) {
                    icono.innerHTML = '<i class="bi bi-check-circle-fill text-success" style="font-size: 3rem;"></i>';
                    titulo.textContent = '¡Devuelto!';
                    texto.textContent = data.message;
                } else {
                    icono.innerHTML = '<i class="bi bi-x-circle-fill text-danger" style="font-size: 3rem;"></i>';
                    titulo.textContent = 'Error';
                    texto.textContent = data.message;
                }
                
                var modalMensaje = new bootstrap.Modal(document.getElementById('modalMensajeDevolucion'));
                modalMensaje.show();
                prestamoADevolver = null;
            });
        });
    }
});

function getCSRFToken() {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.startsWith('csrftoken=')) return c.substring('csrftoken='.length);
    }
    return '';
}