// =============================================
// AGREGAR CHROMEBOOK - VALIDACIONES
// =============================================

// Fecha automática del sistema
document.addEventListener('DOMContentLoaded', function() {
    var hoy = new Date();
    var fecha = hoy.toISOString().split('T')[0];
    document.getElementById('fechaAdquisicion').value = fecha;
});

// Validar código CB-XXX
function validarCodigo() {
    var input = document.getElementById('codigoInput');
    var valor = input.value.replace(/[^0-9]/g, '');
    input.value = valor;
    
    var errorDiv = document.getElementById('errorCodigo');
    if (valor.length > 0 && valor.length < 3) {
        input.classList.add('is-invalid');
        errorDiv.textContent = 'El código debe tener 3 dígitos';
    } else {
        input.classList.remove('is-invalid');
        errorDiv.textContent = '';
    }
}

// Validar formulario antes de enviar
function validarFormulario() {
    var codigo = document.getElementById('codigoInput').value;
    if (codigo.length !== 3) {
        alert('El código debe tener exactamente 3 dígitos (ej: 001)');
        return false;
    }
    return true;
}

// =============================================
// FOTO DEL CHROMEBOOK
// =============================================

// Previsualizar foto seleccionada
function previsualizarFoto(event) {
    var file = event.target.files[0];
    if (file) {
        var reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('imagenPreview').src = e.target.result;
            document.getElementById('previewFoto').style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
}

// Quitar foto
function quitarFoto() {
    document.getElementById('inputFotoChromebook').value = '';
    document.getElementById('previewFoto').style.display = 'none';
    document.getElementById('tokenFotoQR').value = '';
}



function abrirCamara() {
    // Si es dispositivo móvil, usar capture
    if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
        var input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.capture = 'environment';
        input.onchange = function(event) {
            previsualizarFoto(event);
        };
        input.click();
        return;
    }
    
    // Para PC: intentar usar cámara web con getUserMedia
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        // Mostrar modal con cámara
        var camaraHTML = `
            <div class="modal fade" id="modalCamara" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content border-0 shadow-lg" style="border-radius: 16px; overflow: hidden;">
                        <div class="modal-header bg-dark text-white border-0">
                            <h6 class="fw-bold mb-0"><i class="bi bi-camera me-2"></i>Tomar Foto</h6>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body p-0 bg-dark">
                            <video id="videoCamara" autoplay playsinline style="width: 100%; max-height: 400px;"></video>
                            <canvas id="canvasCamara" style="display: none;"></canvas>
                        </div>
                        <div class="modal-footer bg-dark border-0">
                            <button class="btn btn-outline-light btn-sm" data-bs-dismiss="modal">Cancelar</button>
                            <button class="btn btn-light btn-sm" onclick="capturarFoto()">
                                <i class="bi bi-camera-fill me-1"></i>Capturar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Eliminar modal anterior si existe
        var oldModal = document.getElementById('modalCamara');
        if (oldModal) oldModal.remove();
        
        // Insertar nuevo modal
        document.body.insertAdjacentHTML('beforeend', camaraHTML);
        
        // Mostrar modal
        var modalCamara = new bootstrap.Modal(document.getElementById('modalCamara'));
        modalCamara.show();
        
        // Iniciar cámara
        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
            .then(function(stream) {
                var video = document.getElementById('videoCamara');
                video.srcObject = stream;
                video.play();
            })
            .catch(function(err) {
                alert('❌ No se pudo acceder a la cámara. Usa la opción "Archivo" para subir una foto.');
                modalCamara.hide();
            });
        
        // Detener cámara al cerrar modal
        document.getElementById('modalCamara').addEventListener('hidden.bs.modal', function() {
            var video = document.getElementById('videoCamara');
            if (video && video.srcObject) {
                var tracks = video.srcObject.getTracks();
                tracks.forEach(function(track) { track.stop(); });
            }
            this.remove();
        });
        
    } else {
        // Si no hay soporte de cámara, abrir archivo
        document.getElementById('inputFotoChromebook').click();
    }
}

function capturarFoto() {
    var video = document.getElementById('videoCamara');
    var canvas = document.getElementById('canvasCamara');
    var context = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convertir a archivo
    canvas.toBlob(function(blob) {
        var file = new File([blob], 'foto_chromebook.jpg', { type: 'image/jpeg' });
        
        // Crear un DataTransfer para simular un input file
        var dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        document.getElementById('inputFotoChromebook').files = dataTransfer.files;
        
        // Mostrar preview
        var reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('imagenPreview').src = e.target.result;
            document.getElementById('previewFoto').style.display = 'block';
        };
        reader.readAsDataURL(file);
        
        // Cerrar modal
        bootstrap.Modal.getInstance(document.getElementById('modalCamara')).hide();
        
    }, 'image/jpeg', 0.9);
}











// =============================================
// QR PARA FOTO DESDE CELULAR
// =============================================
var tokenFotoQR = null;

function generarQRFoto() {
    var codigo = document.getElementById('codigoInput').value;
    
    // Validar que el código esté completo
    if (!codigo || codigo.length !== 3) {
        mostrarAlerta('⚠️ Campo requerido', 'Debes ingresar el código del Chromebook (3 dígitos) antes de usar el QR.');
        return;
    }
    
    // Validar que la marca esté seleccionada
    var marca = document.querySelector('select[name="marca"]').value;
    if (!marca) {
        mostrarAlerta('⚠️ Campo requerido', 'Debes seleccionar la marca del Chromebook antes de usar el QR.');
        return;
    }
    
    // Validar que el modelo esté lleno
    var modelo = document.querySelector('input[name="modelo"]').value.trim();
    if (!modelo) {
        mostrarAlerta('⚠️ Campo requerido', 'Debes ingresar el modelo del Chromebook antes de usar el QR.');
        return;
    }
    
    // Validar que la serie esté llena
    var serie = document.querySelector('input[name="serie"]').value.trim();
    if (!serie) {
        mostrarAlerta('⚠️ Campo requerido', 'Debes ingresar el número de serie antes de usar el QR.');
        return;
    }
    
    // Si todo está bien, generar QR
    fetch('/prestamos/api/generar-qr-foto-chromebook/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ codigo: 'CB-' + codigo })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            tokenFotoQR = data.token;
            var qrUrl = 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + encodeURIComponent(data.url);
            document.getElementById('qrFotoImagen').src = qrUrl;
            
            var modal = new bootstrap.Modal(document.getElementById('modalQRFoto'));
            modal.show();
        }
    });
}

// Función para mostrar alerta personalizada
function mostrarAlerta(titulo, mensaje) {
    // Crear modal de alerta simple
    var alertaHTML = `
        <div class="modal fade" id="modalAlerta" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered modal-sm">
                <div class="modal-content border-0 shadow-lg" style="border-radius: 16px;">
                    <div class="modal-body text-center p-4">
                        <i class="bi bi-exclamation-triangle text-warning" style="font-size: 3rem;"></i>
                        <h5 class="fw-bold mt-2">${titulo}</h5>
                        <p class="text-muted small">${mensaje}</p>
                        <button class="btn btn-primary btn-sm px-4" data-bs-dismiss="modal">Entendido</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Eliminar modal anterior si existe
    var oldModal = document.getElementById('modalAlerta');
    if (oldModal) oldModal.remove();
    
    // Insertar nuevo modal
    document.body.insertAdjacentHTML('beforeend', alertaHTML);
    
    // Mostrar
    var modalAlerta = new bootstrap.Modal(document.getElementById('modalAlerta'));
    modalAlerta.show();
    
    // Eliminar al cerrar
    document.getElementById('modalAlerta').addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

function verificarFotoQR() {
    if (!tokenFotoQR) return;
    
    // Buscar la foto en el servidor
    var codigo = document.getElementById('codigoInput').value;
    var imgPreview = document.getElementById('imagenPreview');
    imgPreview.src = '/media/chromebooks/CB-' + codigo + '.jpg?t=' + new Date().getTime();
    
    imgPreview.onload = function() {
        document.getElementById('previewFoto').style.display = 'block';
        alert('✅ Foto recibida correctamente');
        bootstrap.Modal.getInstance(document.getElementById('modalQRFoto')).hide();
    };
    
    imgPreview.onerror = function() {
        alert('⚠️ Aún no se recibe la foto. Intenta de nuevo.');
    };
}

function getCSRFToken() {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.startsWith('csrftoken=')) return c.substring('csrftoken='.length);
    }
    return '';
}