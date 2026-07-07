// ============================================================
// Custom Select animado - CRAI UNEMI
// Mejora los <select class="cselect">: dropdown estilizado y con animacion,
// "logo" (monograma de color) por opcion, y opcion de AGREGAR una nueva
// entrada cuando el select trae data-allow-new="Etiqueta".
// Mantiene el <select> nativo sincronizado y dispara su evento 'change',
// para que los onchange existentes (validaciones, submit, etc.) sigan igual.
// ============================================================
(function () {
    var COLORES = ['#1a73e8', '#34a853', '#ea4335', '#f9a825', '#7e57c2', '#00897b', '#e91e63', '#3949ab', '#5d6b7a'];

    function colorDe(txt) {
        var h = 0;
        for (var i = 0; i < txt.length; i++) h = (h * 31 + txt.charCodeAt(i)) >>> 0;
        return COLORES[h % COLORES.length];
    }
    function monograma(txt) { return ((txt || '?').trim().charAt(0) || '?').toUpperCase(); }

    function cerrarTodos(except) {
        var abiertos = document.querySelectorAll('.cs-wrap.abierto');
        for (var i = 0; i < abiertos.length; i++) if (abiertos[i] !== except) abiertos[i].classList.remove('abierto');
    }

    function badgeHTML(opt, label) {
        var logo = opt.getAttribute('data-logo');
        if (logo) return '<img class="cs-logo-img" src="' + logo + '" alt="">';
        if (opt.value) return '<span class="cs-logo" style="background:' + colorDe(label) + '">' + monograma(label) + '</span>';
        return '<span class="cs-logo cs-logo-none"><i class="bi bi-list"></i></span>';
    }

    function construir(sel) {
        if (sel.dataset.csInit) return;
        sel.dataset.csInit = '1';
        var allowNew = sel.getAttribute('data-allow-new');

        var wrap = document.createElement('div');
        wrap.className = 'cs-wrap';
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'cs-btn';
        btn.innerHTML = '<span class="cs-btn-txt"></span><i class="bi bi-chevron-down cs-caret"></i>';
        var panel = document.createElement('div');
        panel.className = 'cs-panel';
        panel.setAttribute('role', 'listbox');

        sel.style.display = 'none';
        sel.parentNode.insertBefore(wrap, sel);
        wrap.appendChild(sel);
        wrap.appendChild(btn);
        wrap.appendChild(panel);

        function elegir(val) {
            sel.value = val;
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            actualizar();
            cerrar();
        }

        function render() {
            panel.innerHTML = '';
            Array.prototype.forEach.call(sel.options, function (opt) {
                var label = opt.textContent.trim();
                var node = document.createElement('div');
                node.className = 'cs-opt' + (opt.value === sel.value ? ' sel' : '') + (opt.disabled ? ' cs-dis' : '');
                node.setAttribute('role', 'option');
                node.dataset.val = opt.value;
                node.innerHTML = badgeHTML(opt, label) + '<span class="cs-opt-txt">' + label + '</span><i class="bi bi-check2 cs-opt-check"></i>';
                if (!opt.disabled) node.addEventListener('click', function () { elegir(opt.value); });
                panel.appendChild(node);
            });

            if (allowNew) {
                var add = document.createElement('div');
                add.className = 'cs-add';
                add.innerHTML = '<i class="bi bi-plus-circle"></i> Agregar ' + allowNew.toLowerCase();
                var box = document.createElement('div');
                box.className = 'cs-newbox';
                box.innerHTML = '<input type="text" class="cs-newinput" placeholder="Nueva ' + allowNew.toLowerCase() + '">' +
                    '<button type="button" class="cs-newok" title="Agregar"><i class="bi bi-check-lg"></i></button>';
                var input = box.querySelector('.cs-newinput');
                var ok = box.querySelector('.cs-newok');

                add.addEventListener('click', function () {
                    add.style.display = 'none';
                    box.classList.add('visible');
                    input.focus();
                });
                function agregar() {
                    var v = input.value.trim();
                    if (!v) { input.focus(); return; }
                    var existe = Array.prototype.some.call(sel.options, function (o) { return o.value.toLowerCase() === v.toLowerCase(); });
                    if (!existe) sel.add(new Option(v, v, true, true));
                    sel.value = v;
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                    render();
                    actualizar();
                    cerrar();
                }
                ok.addEventListener('click', agregar);
                input.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter') { e.preventDefault(); agregar(); }
                });
                panel.appendChild(add);
                panel.appendChild(box);
            }
        }

        function actualizar() {
            var o = sel.options[sel.selectedIndex];
            var t = btn.querySelector('.cs-btn-txt');
            var label = o ? o.textContent.trim() : '';
            if (!o || o.value === '') {
                t.innerHTML = '<span class="cs-ph">' + label + '</span>';
                btn.classList.add('cs-vacio');
            } else {
                t.innerHTML = badgeHTML(o, label) + '<span>' + label + '</span>';
                btn.classList.remove('cs-vacio');
            }
            var nodos = panel.querySelectorAll('.cs-opt');
            for (var i = 0; i < nodos.length; i++) nodos[i].classList.toggle('sel', nodos[i].dataset.val === sel.value);
        }

        function abrir() { cerrarTodos(wrap); wrap.classList.add('abierto'); }
        function cerrar() { wrap.classList.remove('abierto'); }

        btn.addEventListener('click', function (e) { e.stopPropagation(); wrap.classList.contains('abierto') ? cerrar() : abrir(); });
        panel.addEventListener('click', function (e) { e.stopPropagation(); });
        // Si el <select> cambia por fuera (JS externo), reflejarlo.
        sel.addEventListener('cs:refresh', function () { render(); actualizar(); });

        render();
        actualizar();
    }

    function initAll(root) {
        (root || document).querySelectorAll('select.cselect').forEach(construir);
    }

    document.addEventListener('click', function () { cerrarTodos(null); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') cerrarTodos(null); });
    document.addEventListener('DOMContentLoaded', function () { initAll(); });
    window.CSelect = { init: initAll };
})();
