var reservaIdActual = null;
var fotoEvidenciaNombre = null;

document.addEventListener('DOMContentLoaded', function() {
    var modal = document.getElementById('modalCodigoReservacion');
    if (modal) {
        modal.addEventListener('shown.bs.modal', function() {
            document.getElementById('codigoReservacion').focus();
        });
        modal.addEventListener('hidden.bs.modal', function() {
            volverIngresarCodigo();
        });
    }
    
    var campo = document.getElementById('codigoReservacion');
    if (campo) {
        campo.addEventListener('input', function() {
            this.value = this.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
        });
    }
});

function verificarCodigo() {
    var codigo = document.getElementById('codigoReservacion').value.trim().toUpperCase();
    var mensajeError = document.getElementById('mensajeError');
    
    if (codigo.length !== 6) {
        mensajeError.textContent = 'El código debe tener exactamente 6 caracteres.';
        mensajeError.classList.remove('d-none');
        return;
    }
    
    fetch('/prestamos/api/verificar-codigo/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ codigo: codigo })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            mensajeError.classList.add('d-none');
            document.getElementById('detalleNombre').textContent = data.data.nombre;
            document.getElementById('detalleCedula').textContent = data.data.cedula;
            document.getElementById('detalleCarrera').textContent = data.data.carrera;
            document.getElementById('detalleSemestre').textContent = data.data.semestre + 'to';
            document.getElementById('detalleFecha').textContent = data.data.fecha_uso;
            document.getElementById('detalleHorario').textContent = data.data.horario;
            document.getElementById('detalleDuracion').textContent = data.data.duracion;
            document.getElementById('detalleChromebook').textContent = 'Por asignar';
            document.getElementById('detalleEstado').innerHTML = '<span class="badge bg-warning">' + data.data.estado + '</span>';
            reservaIdActual = data.data.reserva_id;
            document.getElementById('pasoIngresarCodigo').style.display = 'none';
            document.getElementById('pasoDetallesReservacion').style.display = 'block';
        } else {
            mensajeError.textContent = data.message || 'Código no encontrado.';
            mensajeError.classList.remove('d-none');
        }
    })
    .catch(function() {
        mensajeError.textContent = 'Error al conectar con el servidor.';
        mensajeError.classList.remove('d-none');
    });
}

function volverIngresarCodigo() {
    document.getElementById('pasoIngresarCodigo').style.display = 'block';
    document.getElementById('pasoDetallesReservacion').style.display = 'none';
    document.getElementById('codigoReservacion').value = '';
    document.getElementById('mensajeError').classList.add('d-none');
    reservaIdActual = null;
    fotoEvidenciaNombre = null;
    window.fotoParaPrestamo = null;
}

function confirmarPrestamo() {
    if (!reservaIdActual) return;
    var modalConfirm = new bootstrap.Modal(document.getElementById('modalConfirmacion'));
    modalConfirm.show();
    document.getElementById('btnConfirmarAccion').onclick = function() {
        modalConfirm.hide();
        ejecutarConfirmacion();
    };
}

function ejecutarConfirmacion() {
    var foto = window.fotoParaPrestamo || fotoEvidenciaNombre || '';
    console.log('📸 Enviando confirmación con foto:', foto);
    
    fetch('/prestamos/api/confirmar-prestamo/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ 
            reserva_id: reservaIdActual,
            foto_nombre: foto
        })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        var icono = document.getElementById('mensajeIcono');
        var titulo = document.getElementById('mensajeTitulo');
        var texto = document.getElementById('mensajeTexto');
        
        if (data.success) {
            icono.innerHTML = '<i class="bi bi-check-circle-fill text-success" style="font-size: 3rem;"></i>';
            titulo.textContent = '¡Préstamo Confirmado!';
            texto.textContent = data.message;
            document.getElementById('btnMensajeCerrar').onclick = function() { location.reload(); };
        } else {
            icono.innerHTML = '<i class="bi bi-x-circle-fill text-danger" style="font-size: 3rem;"></i>';
            titulo.textContent = 'Error';
            texto.textContent = data.message;
        }
        
        var modalMensaje = new bootstrap.Modal(document.getElementById('modalMensaje'));
        modalMensaje.show();
        var modalCodigo = bootstrap.Modal.getInstance(document.getElementById('modalCodigoReservacion'));
        if (modalCodigo) modalCodigo.hide();
    });
}

// =============================================
// QR PARA EVIDENCIA FOTOGRÁFICA
// =============================================
var tokenEvidencia = null;
var intervaloVerificacion = null;
var intervaloRefreshQR = null;
var tiempoRestante = 120;

function abrirCamaraEvidencia() {
    if (!reservaIdActual) {
        alert('Primero verifica un código de reservación.');
        return;
    }
    
    // Limpiar estado anterior del modal QR
    document.getElementById('qrContainer').style.display = 'inline-block';
    document.getElementById('vistaPreviaContainer').style.display = 'none';
    document.getElementById('qrImagen').style.opacity = '1';
    document.getElementById('estadoEvidencia').innerHTML = 'Esperando foto...';
    document.getElementById('btnConfirmarDespuesQR').disabled = true;
    fotoEvidenciaNombre = null;
    window.fotoParaPrestamo = null;
    
    generarNuevoQR();
    
    var modalQR = new bootstrap.Modal(document.getElementById('modalQREvidencia'));
    modalQR.show();
    
    document.getElementById('modalQREvidencia').addEventListener('hidden.bs.modal', function() {
        clearInterval(intervaloVerificacion);
        clearInterval(intervaloRefreshQR);
    });
}

function generarNuevoQR() {
    tiempoRestante = 45;
    fotoEvidenciaNombre = null;
    document.getElementById('btnConfirmarDespuesQR').disabled = true;
    document.getElementById('estadoEvidencia').innerHTML = '<span class="text-warning"><i class="bi bi-hourglass-split"></i> Esperando foto... (' + tiempoRestante + 's)</span>';
    
    if (intervaloVerificacion) clearInterval(intervaloVerificacion);
    if (intervaloRefreshQR) clearInterval(intervaloRefreshQR);
    
    fetch('/prestamos/api/generar-qr-evidencia/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ reserva_id: reservaIdActual, tipo: 'entrega' })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            tokenEvidencia = data.token;
            var qrUrl = 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + encodeURIComponent(data.url);
            document.getElementById('qrImagen').src = qrUrl;
            intervaloVerificacion = setInterval(verificarEvidencia, 3000);
            intervaloRefreshQR = setInterval(actualizarContadorQR, 1000);
        }
    });
}

function actualizarContadorQR() {
    tiempoRestante--;
    if (tiempoRestante <= 0) {
        clearInterval(intervaloRefreshQR);
        document.getElementById('estadoEvidencia').innerHTML = '<span class="text-info"><i class="bi bi-arrow-repeat"></i> Generando nuevo QR...</span>';
        document.getElementById('qrImagen').style.opacity = '0.5';
        setTimeout(function() {
            document.getElementById('qrImagen').style.opacity = '1';
            generarNuevoQR();
        }, 1000);
    } else if (tiempoRestante <= 30) {
        document.getElementById('estadoEvidencia').innerHTML = '<span class="text-warning"><i class="bi bi-hourglass-split"></i> Esperando foto... (' + tiempoRestante + 's) ⚠️</span>';
    } else {
        document.getElementById('estadoEvidencia').innerHTML = '<span class="text-warning"><i class="bi bi-hourglass-split"></i> Esperando foto... (' + tiempoRestante + 's)</span>';
    }
}

function verificarEvidencia() {
    if (!tokenEvidencia) return;
    
    fetch('/prestamos/api/verificar-evidencia/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ token: tokenEvidencia })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.recibida) {
            clearInterval(intervaloVerificacion);
            clearInterval(intervaloRefreshQR);
            
            document.getElementById('btnConfirmarDespuesQR').disabled = false;
            document.getElementById('estadoEvidencia').innerHTML = '<span class="text-success"><i class="bi bi-check-circle"></i> ¡Foto recibida! Haz clic en Continuar.</span>';
            document.getElementById('qrImagen').style.opacity = '0.5';
            
            // Guardar nombre de foto
            fotoEvidenciaNombre = data.nombre_archivo || '';
            console.log('📸 Foto guardada en variable:', fotoEvidenciaNombre);
            
            // Ocultar QR y mostrar check verde
            document.getElementById('qrContainer').style.display = 'none';
            document.getElementById('vistaPreviaContainer').style.display = 'block';
            document.getElementById('vistaPreviaContainer').innerHTML = 
                '<i class="bi bi-check-circle-fill text-success" style="font-size: 5rem;"></i>' +
                '<p class="small text-success fw-bold mt-2">¡Foto recibida correctamente!</p>';
        }
    });
}

function cerrarModalQR() {
    clearInterval(intervaloVerificacion);
    clearInterval(intervaloRefreshQR);
    
    // Guardar en variable global para que no se pierda
    window.fotoParaPrestamo = fotoEvidenciaNombre;
    console.log('📸 Cerrando QR. Foto guardada:', window.fotoParaPrestamo);
    
    var modalQR = document.getElementById('modalQREvidencia');
    var modalInstance = bootstrap.Modal.getInstance(modalQR);
    if (modalInstance) modalInstance.hide();
    
    setTimeout(function() {
        var backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) backdrop.remove();
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        confirmarPrestamo();
    }, 300);
}

// =============================================
// DETALLE DE PRÉSTAMO
// =============================================
function verDetallePrestamo(id) {
    fetch('/prestamos/api/detalle-prestamo/' + id + '/')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                document.getElementById('detallePrestamoIdHeader').textContent = '#' + data.data.id;
                document.getElementById('detallePrestamoEstudiante').innerHTML = '<strong>' + data.data.estudiante + '</strong>';
                document.getElementById('detallePrestamoChromebook').innerHTML = '<strong>' + data.data.chromebook + '</strong>';
                
                var fechaPrestamo = data.data.fecha_prestamo.split(' ');
                var fechaDev = data.data.devolucion.split(' ');
                
                document.getElementById('detallePrestamoFecha').innerHTML = 
                    '<strong>' + fechaPrestamo[0] + '</strong><br><small class="text-muted">' + (fechaPrestamo[1] || '') + '</small>';
                
                document.getElementById('detallePrestamoDevolucion').innerHTML = 
                    '<strong>' + fechaDev[0] + '</strong><br><small class="text-muted">' + (fechaDev[1] || '') + '</small>';
                
                var estadoClass = data.data.estado === 'activo' ? 'success' : (data.data.estado === 'devuelto' ? 'info' : 'danger');
                document.getElementById('detallePrestamoEstado').innerHTML = '<span class="badge bg-' + estadoClass + ' px-3 py-2"><strong>' + data.data.estado.toUpperCase() + '</strong></span>';
                
                var fotoImg = document.getElementById('detalleFotoEvidencia');
                var sinFoto = document.getElementById('detalleSinFoto');
                if (data.data.foto_url) {
                    fotoImg.src = data.data.foto_url;
                    fotoImg.style.display = 'block';
                    sinFoto.style.display = 'none';
                } else {
                    fotoImg.style.display = 'none';
                    sinFoto.style.display = 'block';
                }
                
                var modal = new bootstrap.Modal(document.getElementById('modalDetallePrestamo'));
                modal.show();
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