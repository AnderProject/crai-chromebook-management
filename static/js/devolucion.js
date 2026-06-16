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

// =============================================
// TIEMPO RESTANTE EN TIEMPO REAL
// =============================================
function actualizarTiemposRestantes() {
    document.querySelectorAll('.tiempo-restante').forEach(function(el) {
        var fechaDevolucion = new Date(el.getAttribute('data-devolucion'));
        var ahora = new Date();
        var diferencia = fechaDevolucion - ahora;
        
        if (diferencia <= 0) {
            el.innerHTML = '<span style="color: #dc3545; font-weight: 700;">⚠️ VENCIDO</span>';
            el.style.animation = 'alertaVencido 1s infinite';
        } else {
            var horas = Math.floor(diferencia / (1000 * 60 * 60));
            var minutos = Math.floor((diferencia % (1000 * 60 * 60)) / (1000 * 60));
            
            if (horas < 1) {
                el.innerHTML = '<span style="color: #dc3545; font-weight: 700;">⏰ ' + minutos + 'min restantes</span>';
            } else if (horas < 2) {
                el.innerHTML = '<span style="color: #dc3545; font-weight: 700;">⏰ ' + horas + 'h ' + minutos + 'min</span>';
            } else if (horas < 4) {
                el.innerHTML = '<span style="color: #ff9800; font-weight: 600;">🟡 ' + horas + 'h ' + minutos + 'min</span>';
            } else {
                el.innerHTML = '<span style="color: #28a745;">🟢 ' + horas + 'h ' + minutos + 'min</span>';
            }
        }
    });
}

// Actualizar cada 30 segundos
setInterval(actualizarTiemposRestantes, 30000);

// Ejecutar al cargar
document.addEventListener('DOMContentLoaded', function() {
    actualizarTiemposRestantes();
});