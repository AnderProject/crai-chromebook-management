var paginaActual = 1;
var tarjetasPorPagina = 6;

document.addEventListener('DOMContentLoaded', function() {
    inicializarPaginacion();
    actualizarProgresos();
    setInterval(actualizarProgresos, 30000);
});

function inicializarPaginacion() {
    var tarjetas = document.querySelectorAll('.reserva-card-compact');
    var totalPaginas = Math.ceil(tarjetas.length / tarjetasPorPagina);
    
    if (totalPaginas <= 1) {
        document.getElementById('paginacionReservas').style.display = 'none';
        return;
    }
    
    var numsHtml = '';
    for (var i = 1; i <= totalPaginas; i++) {
        numsHtml += '<button class="btn-pag' + (i === 1 ? ' activo' : '') + '" onclick="irPagina(' + i + ')">' + i + '</button>';
    }
    document.getElementById('paginasNumeros').innerHTML = numsHtml;
    mostrarPagina(1);
}

function mostrarPagina(pagina) {
    var tarjetas = document.querySelectorAll('.reserva-card-compact');
    var inicio = (pagina - 1) * tarjetasPorPagina;
    var fin = inicio + tarjetasPorPagina;
    
    tarjetas.forEach(function(t, i) {
        t.style.display = (i >= inicio && i < fin) ? 'flex' : 'none';
    });
    paginaActual = pagina;
    
    document.querySelectorAll('.pag-nums .btn-pag').forEach(function(b) { b.classList.remove('activo'); });
    var botones = document.querySelectorAll('.pag-nums .btn-pag');
    if (botones[pagina - 1]) botones[pagina - 1].classList.add('activo');
    
    document.getElementById('btnAnterior').disabled = pagina <= 1;
    document.getElementById('btnSiguiente').disabled = pagina >= Math.ceil(tarjetas.length / tarjetasPorPagina);
}

function irPagina(p) { mostrarPagina(p); }

function cambiarPagina(dir) {
    var total = Math.ceil(document.querySelectorAll('.reserva-card-compact').length / tarjetasPorPagina);
    if (dir === 'anterior' && paginaActual > 1) mostrarPagina(paginaActual - 1);
    if (dir === 'siguiente' && paginaActual < total) mostrarPagina(paginaActual + 1);
}

function actualizarProgresos() {
    document.querySelectorAll('.progreso-live').forEach(function(prog) {
        var ahora = new Date();
        var inicio = prog.getAttribute('data-inicio');
        var fin = prog.getAttribute('data-fin');
        if (!inicio || !fin) return;
        
        var pi = inicio.split(':'), pf = fin.split(':');
        var dInicio = new Date(ahora); dInicio.setHours(pi[0], pi[1], 0, 0);
        var dFin = new Date(ahora); dFin.setHours(pf[0], pf[1], 0, 0);
        
        var total = dFin - dInicio, trans = ahora - dInicio;
        var pct = Math.min(100, Math.max(0, (trans / total) * 100));
        
        prog.querySelector('.progreso-live-fill').style.width = pct + '%';
        
        var restante = dFin - ahora;
        var tiempo = prog.querySelector('.progreso-live-time');
        if (restante <= 0) { tiempo.textContent = 'Vencido'; }
        else {
            var h = Math.floor(restante / 3600000), m = Math.floor((restante % 3600000) / 60000);
            tiempo.textContent = h + 'h ' + m + 'm';
        }
    });
}