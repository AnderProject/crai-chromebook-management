// =============================================
// TIME PICKER (menú desplegable) - CRAI UNEMI
// Componente reutilizable de selección de hora.
//
// Marcado esperado por cada selector:
//   <div class="timepicker" data-tp-min="08:00" data-tp-max="17:00"
//        data-tp-step="30" [data-tp-after="idDeOtroHidden"]>
//     <button type="button" class="timepicker-field">
//       <i class="bi bi-clock"></i>
//       <span class="timepicker-valor">08:00</span>
//       <i class="bi bi-chevron-down timepicker-caret"></i>
//     </button>
//     <div class="timepicker-panel" role="listbox"></div>
//     <input type="hidden" id="horaInicio" name="hora_inicio" value="08:00">
//   </div>
//
// API pública (window.CraiTP), todas las claves usan el id del input hidden:
//   CraiTP.get(id)            -> 'HH:MM'
//   CraiTP.set(id, val, user) -> fija el valor (snap a la rejilla si hace falta)
//   CraiTP.setMin(id, val)    -> deshabilita las horas anteriores a val
//   CraiTP.setAhora(id, val)  -> agrega/actualiza la opción "Ahora · val" (null la quita)
//   CraiTP.onChange(id, cb)   -> escucha el evento 'tp:change' (detail: {value, byUser})
//
// data-tp-after enlaza un selector de "fin" al de "inicio": las horas <= inicio
// se deshabilitan y, si el valor de fin queda inválido, se sube automáticamente.
// =============================================

(function () {
    var REG = {};       // id del hidden -> estado del selector
    var abierto = null; // selector con el panel abierto

    function pad(n) { return (n < 10 ? '0' : '') + n; }
    function aStr(m) { return pad(Math.floor(m / 60)) + ':' + pad(m % 60); }
    function aMin(s) { var p = (s || '0:0').split(':'); return (+p[0]) * 60 + (+p[1]); }

    function init(container) {
        var hidden = container.querySelector('input[type="hidden"]');
        if (!hidden || !hidden.id) { return; }

        var st = {
            container: container,
            field: container.querySelector('.timepicker-field'),
            valor: container.querySelector('.timepicker-valor'),
            panel: container.querySelector('.timepicker-panel'),
            hidden: hidden,
            min: aMin(container.dataset.tpMin || '08:00'),
            max: aMin(container.dataset.tpMax || '17:00'),
            step: parseInt(container.dataset.tpStep || '30', 10),
            after: container.dataset.tpAfter || null,
            ahora: null,    // minutos de la opción "Ahora", o null
            minEff: null    // hora mínima seleccionable (minutos), o null = min
        };
        REG[hidden.id] = st;

        st.field.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            toggle(st);
        });

        render(st);
        fijar(hidden.id, hidden.value || aStr(st.min), false, true);
    }

    // Dibuja las opciones del panel según min/max/step + "Ahora" + deshabilitadas.
    function render(st) {
        st.panel.innerHTML = '';
        var minEff = (st.minEff != null) ? st.minEff : st.min;

        if (st.ahora != null) {
            st.panel.appendChild(
                opcion(st, st.ahora, 'Ahora · ' + aStr(st.ahora), st.ahora < minEff, true)
            );
        }
        for (var m = st.min; m <= st.max; m += st.step) {
            st.panel.appendChild(opcion(st, m, aStr(m), m < minEff, false));
        }
        marcar(st);
    }

    function opcion(st, minVal, etiqueta, deshab, esAhora) {
        var div = document.createElement('div');
        div.className = 'timepicker-opcion'
            + (esAhora ? ' tp-ahora' : '')
            + (deshab ? ' deshabilitada' : '');
        div.setAttribute('role', 'option');
        div.dataset.valor = aStr(minVal);
        div.textContent = etiqueta;
        div.addEventListener('click', function (e) {
            e.stopPropagation();
            if (this.classList.contains('deshabilitada')) { return; }
            fijar(st.hidden.id, this.dataset.valor, true, false);
            cerrar(st);
        });
        return div;
    }

    // Marca como activa la opción cuyo valor coincide con el hidden.
    function marcar(st) {
        var actual = st.hidden.value;
        var ops = st.panel.querySelectorAll('.timepicker-opcion');
        for (var i = 0; i < ops.length; i++) {
            ops[i].classList.toggle('activo', ops[i].dataset.valor === actual);
        }
    }

    // Devuelve el valor (minutos) de la primera opción no deshabilitada.
    function primerHabilitado(st) {
        var op = st.panel.querySelector('.timepicker-opcion:not(.deshabilitada)');
        return op ? aMin(op.dataset.valor) : null;
    }

    // Fija el valor del selector. Si no cae en una opción válida, lo sube
    // a la primera hora de la rejilla >= valor (snap).
    function fijar(id, valor, byUser, silent) {
        var st = REG[id];
        if (!st) { return; }

        var vMin = aMin(valor);
        var existe = (st.ahora != null && vMin === st.ahora) ||
            (vMin >= st.min && vMin <= st.max && ((vMin - st.min) % st.step === 0));
        if (!existe) {
            // snap a la siguiente hora de la rejilla dentro del rango
            var snap = st.min + Math.ceil((vMin - st.min) / st.step) * st.step;
            if (snap < st.min) { snap = st.min; }
            if (snap > st.max) { snap = st.max; }
            vMin = snap;
            valor = aStr(snap);
        }

        st.hidden.value = valor;
        st.valor.textContent = (st.ahora != null && vMin === st.ahora) ? ('Ahora · ' + valor) : valor;
        marcar(st);
        aplicarEnlaces(id);

        if (!silent) {
            st.hidden.dispatchEvent(new CustomEvent('tp:change', {
                bubbles: true,
                detail: { value: valor, byUser: !!byUser }
            }));
        }
    }

    // Reaplica la restricción a los selectores enlazados (fin debe ser > inicio).
    function aplicarEnlaces(srcId) {
        Object.keys(REG).forEach(function (fid) {
            var st = REG[fid];
            if (st.after !== srcId) { return; }
            var inicioMin = aMin(REG[srcId].hidden.value);
            st.minEff = inicioMin + 1;           // estrictamente mayor que inicio
            render(st);
            if (aMin(st.hidden.value) <= inicioMin) {
                var nuevo = primerHabilitado(st);
                if (nuevo != null) { fijar(fid, aStr(nuevo), false, false); }
            } else {
                marcar(st);
            }
        });
    }

    // --------- apertura / cierre del panel ---------
    function toggle(st) {
        if (abierto === st) { cerrar(st); }
        else { if (abierto) { cerrar(abierto); } abrir(st); }
    }

    function abrir(st) {
        st.container.classList.add('abierto');
        st.field.setAttribute('aria-expanded', 'true');
        abierto = st;
        var act = st.panel.querySelector('.timepicker-opcion.activo')
            || st.panel.querySelector('.timepicker-opcion:not(.deshabilitada)');
        if (act) {
            st.panel.scrollTop = act.offsetTop - (st.panel.clientHeight / 2) + (act.offsetHeight / 2);
        }
    }

    function cerrar(st) {
        st.container.classList.remove('abierto');
        st.field.setAttribute('aria-expanded', 'false');
        if (abierto === st) { abierto = null; }
    }

    document.addEventListener('click', function () { if (abierto) { cerrar(abierto); } });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && abierto) { cerrar(abierto); }
    });

    // --------- API pública ---------
    window.CraiTP = {
        get: function (id) { return REG[id] ? REG[id].hidden.value : ''; },
        set: function (id, val, byUser) { fijar(id, val, byUser, false); },
        setMin: function (id, val) {
            var st = REG[id];
            if (!st) { return; }
            st.minEff = aMin(val);
            render(st);
            if (aMin(st.hidden.value) < st.minEff) {
                var n = primerHabilitado(st);
                if (n != null) { fijar(id, aStr(n), false, false); }
            }
        },
        setAhora: function (id, val) {
            var st = REG[id];
            if (!st) { return; }
            st.ahora = (val == null) ? null : aMin(val);
            render(st);
        },
        clearAhora: function (id) { this.setAhora(id, null); },
        onChange: function (id, cb) {
            var st = REG[id];
            if (st) { st.hidden.addEventListener('tp:change', cb); }
        }
    };

    document.addEventListener('DOMContentLoaded', function () {
        var nodos = document.querySelectorAll('.timepicker');
        for (var i = 0; i < nodos.length; i++) { init(nodos[i]); }
    });
})();
