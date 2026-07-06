// =============================================
// REGISTRAR MANTENIMIENTO
// La garantía se determina automáticamente según el equipo elegido:
//  - En garantía vigente -> "¿En garantía?" = Sí.
//  - Sin garantía        -> "¿En garantía?" = No.
// =============================================
function aplicarGarantiaEquipo() {
    var select = document.getElementById('mantChromebook');
    var opt = select.options[select.selectedIndex];
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
        garantiaHint.textContent = 'Se determina automáticamente al elegir el equipo.';
        return;
    }

    if (enGarantia) {
        radioSi.checked = true;
        var fin = opt.getAttribute('data-fin');
        garantiaHint.textContent = fin ? ('En garantía hasta el ' + fin + '.') : 'Equipo en garantía vigente.';
    } else {
        radioNo.checked = true;
        garantiaHint.textContent = 'Este equipo no tiene garantía vigente.';
    }
}

document.addEventListener('DOMContentLoaded', aplicarGarantiaEquipo);
