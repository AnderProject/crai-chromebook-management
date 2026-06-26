// =============================================
// REGISTRAR MANTENIMIENTO
// La garantía y el costo se determinan automáticamente según el equipo:
//  - En garantía vigente -> costo 0 y bloqueado, "¿En garantía?" = Sí.
//  - Sin garantía        -> costo editable, "¿En garantía?" = No.
// =============================================
function aplicarGarantiaEquipo() {
    var select = document.getElementById('mantChromebook');
    var opt = select.options[select.selectedIndex];
    var costo = document.getElementById('mantCosto');
    var costoHint = document.getElementById('costoHint');
    var garantiaHint = document.getElementById('garantiaHint');
    var radioSi = document.getElementById('garantiaSi');
    var radioNo = document.getElementById('garantiaNo');

    // El usuario no edita la garantía manualmente: refleja el dato del equipo.
    // No usamos disabled (un radio deshabilitado no envía su valor en el POST);
    // el bloqueo visual lo hace .mant-seg-auto con pointer-events:none.
    var enGarantia = opt && opt.getAttribute('data-garantia') === '1';

    if (!select.value) {
        // Sin equipo elegido: estado neutro.
        radioNo.checked = true;
        costo.value = '0';
        costo.readOnly = false;
        costo.classList.remove('mant-input-bloqueado');
        costoHint.textContent = '';
        garantiaHint.textContent = 'Se determina automáticamente al elegir el equipo.';
        return;
    }

    if (enGarantia) {
        radioSi.checked = true;
        costo.value = '0';
        costo.readOnly = true;
        costo.classList.add('mant-input-bloqueado');
        var fin = opt.getAttribute('data-fin');
        costoHint.textContent = 'Equipo en garantía: el costo es $0.';
        garantiaHint.textContent = fin ? ('En garantía hasta el ' + fin + '.') : 'Equipo en garantía vigente.';
    } else {
        radioNo.checked = true;
        costo.readOnly = false;
        costo.classList.remove('mant-input-bloqueado');
        if (costo.value === '0') costo.value = '';
        costoHint.textContent = 'Equipo sin garantía: ingresa el costo del mantenimiento.';
        garantiaHint.textContent = 'Este equipo no tiene garantía vigente.';
    }
}

document.addEventListener('DOMContentLoaded', aplicarGarantiaEquipo);
