// =============================================
// SELECTOR DE HORA TIPO RUEDAS (modal estilo alarma)
// Componente reutilizable: window.abrirRuedaHora(opts)
//   opts = {
//     titulo:   'Hora de inicio',
//     valor:    'HH:MM',           // valor inicial
//     minHora:  8,  maxHora: 17,   // rango de horas (inclusive)
//     pasoMin:  30,                // intervalo de minutos
//     onConfirm: function (valor) {}
//   }
// =============================================
(function () {
    var ITEM_H = 44;        // alto de cada item (coincide con el CSS)
    var modal, colHoras, colMin, tituloEl, _onConfirm;

    function pad2(n) { return (n < 10 ? '0' : '') + n; }

    function construir() {
        if (modal) { return; }
        modal = document.createElement('div');
        modal.className = 'rueda-overlay';
        modal.innerHTML =
            '<div class="rueda-card">' +
            '  <div class="rueda-titulo" id="ruedaTitulo">Selecciona la hora</div>' +
            '  <div class="rueda-cuerpo">' +
            '    <div class="rueda-banda"></div>' +
            '    <div class="rueda-col" id="ruedaHoras"></div>' +
            '    <div class="rueda-sep">:</div>' +
            '    <div class="rueda-col" id="ruedaMin"></div>' +
            '  </div>' +
            '  <div class="rueda-acciones">' +
            '    <button type="button" class="rueda-btn rueda-cancel">Cancelar</button>' +
            '    <button type="button" class="rueda-btn rueda-ok">Aceptar</button>' +
            '  </div>' +
            '</div>';
        document.body.appendChild(modal);

        colHoras = modal.querySelector('#ruedaHoras');
        colMin = modal.querySelector('#ruedaMin');
        tituloEl = modal.querySelector('#ruedaTitulo');

        modal.querySelector('.rueda-cancel').addEventListener('click', cerrar);
        modal.querySelector('.rueda-ok').addEventListener('click', confirmar);
        modal.addEventListener('click', function (e) { if (e.target === modal) { cerrar(); } });

        var marcarH = debounceCentro(colHoras);
        var marcarM = debounceCentro(colMin);
        colHoras.addEventListener('scroll', marcarH);
        colMin.addEventListener('scroll', marcarM);
    }

    function debounceCentro(col) {
        var t = null;
        return function () {
            marcarCentro(col);
            if (t) { clearTimeout(t); }
            t = setTimeout(function () { ajustarSnap(col); }, 90);
        };
    }

    function llenar(col, valores, sel) {
        col.innerHTML = '';
        var padTop = document.createElement('div'); padTop.className = 'rueda-pad';
        col.appendChild(padTop);
        valores.forEach(function (v, i) {
            var it = document.createElement('div');
            it.className = 'rueda-item';
            it.textContent = v;
            it.dataset.index = i;
            it.addEventListener('click', function () { centrar(col, i); });
            col.appendChild(it);
        });
        var padBot = document.createElement('div'); padBot.className = 'rueda-pad';
        col.appendChild(padBot);
        col._valores = valores;
        var idx = valores.indexOf(sel);
        if (idx < 0) { idx = 0; }
        col.scrollTop = idx * ITEM_H;
        marcarCentro(col);
    }

    function indiceCentro(col) {
        var idx = Math.round(col.scrollTop / ITEM_H);
        var max = (col._valores ? col._valores.length : 1) - 1;
        return Math.min(Math.max(idx, 0), max);
    }

    function marcarCentro(col) {
        var centro = indiceCentro(col);
        col.querySelectorAll('.rueda-item').forEach(function (it) {
            it.classList.toggle('activo', parseInt(it.dataset.index, 10) === centro);
        });
    }

    function ajustarSnap(col) {
        var idx = indiceCentro(col);
        var destino = idx * ITEM_H;
        if (Math.abs(col.scrollTop - destino) > 1) {
            col.scrollTo({ top: destino, behavior: 'smooth' });
        }
    }

    function centrar(col, i) {
        col.scrollTo({ top: i * ITEM_H, behavior: 'smooth' });
        setTimeout(function () { marcarCentro(col); }, 60);
    }

    function confirmar() {
        var h = colHoras._valores[indiceCentro(colHoras)];
        var m = colMin._valores[indiceCentro(colMin)];
        var valor = h + ':' + m;
        cerrar();
        if (typeof _onConfirm === 'function') { _onConfirm(valor); }
    }

    function cerrar() {
        if (modal) { modal.classList.remove('visible'); }
    }

    window.abrirRuedaHora = function (opts) {
        construir();
        _onConfirm = opts.onConfirm;
        tituloEl.textContent = opts.titulo || 'Selecciona la hora';

        var horas = [];
        var minHora = (opts.minHora != null) ? opts.minHora : 0;
        var maxHora = (opts.maxHora != null) ? opts.maxHora : 23;
        for (var h = minHora; h <= maxHora; h++) { horas.push(pad2(h)); }

        var minutos = [];
        var paso = opts.pasoMin || 5;
        for (var m = 0; m < 60; m += paso) { minutos.push(pad2(m)); }

        var partes = (opts.valor || (pad2(minHora) + ':00')).split(':');
        var selH = pad2(parseInt(partes[0], 10) || minHora);
        var selM = partes[1] || '00';
        // si el minuto exacto no está en la lista, usar el más cercano disponible
        if (minutos.indexOf(selM) < 0) {
            var mNum = parseInt(selM, 10) || 0;
            var cercano = minutos.reduce(function (a, b) {
                return Math.abs(parseInt(b, 10) - mNum) < Math.abs(parseInt(a, 10) - mNum) ? b : a;
            }, minutos[0]);
            selM = cercano;
        }

        modal.classList.add('visible');
        requestAnimationFrame(function () {
            llenar(colHoras, horas, selH);
            llenar(colMin, minutos, selM);
        });
    };
})();
