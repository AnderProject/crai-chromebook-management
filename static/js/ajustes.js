// =============================================
// AJUSTES - CRAI UNEMI
// Modo oscuro y preferencias
// =============================================

function toggleModoOscuro() {
    var activo = document.getElementById('modoOscuro').checked;
    
    if (activo) {
        document.body.classList.add('modo-oscuro');
        localStorage.setItem('modoOscuro', 'true');
    } else {
        document.body.classList.remove('modo-oscuro');
        localStorage.setItem('modoOscuro', 'false');
    }
}

// Cargar preferencia al iniciar
document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('modoOscuro') === 'true') {
        document.getElementById('modoOscuro').checked = true;
        document.body.classList.add('modo-oscuro');
    }
});


// =============================================
// INTEGRACIÓN API MATRÍCULAS
// =============================================

function testConexionAPI() {
    var statusEl = document.getElementById('apiStatus');
    statusEl.innerHTML = '<span class="badge bg-info fs-6 px-3 py-2"><i class="bi bi-hourglass me-1"></i>Verificando...</span>';
    if (typeof mostrarLoader === 'function') mostrarLoader();

    fetch('/prestamos/api/test-conexion/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            statusEl.innerHTML = '<span class="badge bg-success fs-6 px-3 py-2"><i class="bi bi-check-circle me-1"></i>' + data.message + '</span>';
        } else {
            statusEl.innerHTML = '<span class="badge bg-danger fs-6 px-3 py-2"><i class="bi bi-x-circle me-1"></i>' + data.message + '</span>';
        }
    })
    .catch(function() {
        statusEl.innerHTML = '<span class="badge bg-danger fs-6 px-3 py-2"><i class="bi bi-x-circle me-1"></i>Error de red al verificar conexión</span>';
    })
    .finally(function() {
        if (typeof ocultarLoader === 'function') ocultarLoader();
    });
}

function sincronizarEstudiantes() {
    var btn = document.getElementById('btnSincronizar');
    var statusEl = document.getElementById('apiStatus');
    btn.disabled = true;
    btn.style.opacity = '0.6';
    statusEl.innerHTML = '<span class="badge bg-info fs-6 px-3 py-2"><i class="bi bi-hourglass me-1"></i>Sincronizando estudiantes...</span>';
    if (typeof mostrarLoader === 'function') mostrarLoader();

    fetch('/prestamos/api/sincronizar/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            statusEl.innerHTML = '<span class="badge bg-success fs-6 px-3 py-2"><i class="bi bi-check-circle me-1"></i>' + data.message + '</span>';
        } else {
            statusEl.innerHTML = '<span class="badge bg-danger fs-6 px-3 py-2"><i class="bi bi-x-circle me-1"></i>' + data.message + '</span>';
        }
    })
    .catch(function() {
        statusEl.innerHTML = '<span class="badge bg-danger fs-6 px-3 py-2"><i class="bi bi-x-circle me-1"></i>Error de red al sincronizar</span>';
    })
    .finally(function() {
        btn.disabled = false;
        btn.style.opacity = '1';
        if (typeof ocultarLoader === 'function') ocultarLoader();
    });
}

function getCSRFToken() {
    var name = 'csrftoken';
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.indexOf(name + '=') === 0) {
            return c.substring(name.length + 1);
        }
    }
    return '';
}

// =============================================
// CONECTAR / DESCONECTAR API DE MATRÍCULAS
// =============================================
function toggleApiMatriculas() {
    var btn = document.getElementById('btnToggleApi');
    var desconectando = btn.classList.contains('desconectar');
    var verbo = desconectando ? 'desconectar' : 'conectar';
    if (!confirm('¿Seguro que deseas ' + verbo + ' la API de matrículas?')) { return; }

    fetch('/prestamos/api/toggle-matriculas/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        var estado = document.getElementById('apiConexionEstado');
        var texto = document.getElementById('btnToggleApiTexto');
        if (data.activa) {
            estado.innerHTML = '<span class="badge-conexion conectada"><i class="bi bi-broadcast"></i>Conectada</span>';
            btn.classList.remove('conectar'); btn.classList.add('desconectar');
            btn.querySelector('i').className = 'bi bi-plug-fill me-1';
            texto.textContent = 'Desconectar API';
            if (typeof mostrarToast === 'function') mostrarToast('API de matrículas conectada.', 'success');
        } else {
            estado.innerHTML = '<span class="badge-conexion desconectada"><i class="bi bi-plug"></i>Desconectada</span>';
            btn.classList.remove('desconectar'); btn.classList.add('conectar');
            btn.querySelector('i').className = 'bi bi-plug me-1';
            texto.textContent = 'Conectar API';
            if (typeof mostrarToast === 'function') mostrarToast('API de matrículas desconectada.', 'warning');
        }
        document.getElementById('apiStatus').innerHTML = '';
    });
}
