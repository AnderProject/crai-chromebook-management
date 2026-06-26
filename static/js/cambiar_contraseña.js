document.addEventListener('DOMContentLoaded', function () {
    const inputNueva     = document.getElementById('nueva_contraseña');
    const inputConfirmar = document.getElementById('confirmar_contraseña');
    const btnToggle      = document.getElementById('btnTogglePass');
    const btnFinal       = document.getElementById('btnCambiarFinal');
    const form           = document.getElementById('formCambiarContrasena');
    const matchDiv       = document.getElementById('matchIndicador');
    const fortalezaWrap  = document.getElementById('fortalezaWrap');
    const textoF         = document.getElementById('fortalezaTexto');
    const barras         = ['fb1', 'fb2', 'fb3', 'fb4'].map(id => document.getElementById(id));

    if (!inputNueva) return; // página en estado cambio_exitoso; nada que hacer

    /* ── Toggle mostrar/ocultar contraseña ── */
    if (btnToggle) {
        btnToggle.addEventListener('click', function () {
            const visible = inputNueva.type === 'text';
            inputNueva.type = visible ? 'password' : 'text';
            this.querySelector('i').className = visible ? 'bi bi-eye-fill' : 'bi bi-eye-slash-fill';
        });
    }

    /* ── Indicador de fortaleza ── */
    const niveles = [
        { texto: 'Muy débil',  color: '#ef4444' },
        { texto: 'Débil',      color: '#f97316' },
        { texto: 'Moderada',   color: '#eab308' },
        { texto: 'Fuerte',     color: '#22c55e' },
    ];

    function calcularFortaleza(pw) {
        let score = 0;
        if (pw.length >= 8)             score++;
        if (pw.length >= 12)            score++;
        if (/[A-Z]/.test(pw))          score++;
        if (/[0-9]/.test(pw))          score++;
        if (/[^A-Za-z0-9]/.test(pw))  score++;
        return Math.min(4, Math.max(0, score));
    }

    function actualizarFortaleza(pw) {
        if (!fortalezaWrap) return;
        if (pw.length === 0) {
            fortalezaWrap.classList.remove('visible');
            return;
        }
        fortalezaWrap.classList.add('visible');
        const nivel = calcularFortaleza(pw);
        const info  = niveles[Math.max(0, nivel - 1)];
        barras.forEach((b, i) => {
            if (b) b.style.background = i < nivel ? info.color : '#e5e7eb';
        });
        if (textoF) {
            textoF.textContent = nivel > 0 ? info.texto : 'Muy débil';
            textoF.style.color = nivel > 0 ? info.color : '#ef4444';
        }
    }

    /* ── Indicador de coincidencia ── */
    function actualizarMatch() {
        if (!matchDiv) return;
        const nv = inputNueva.value;
        const cf = inputConfirmar.value;
        if (cf.length === 0) {
            matchDiv.style.display = 'none';
            inputConfirmar.classList.remove('is-valid', 'is-invalid');
            return;
        }
        matchDiv.style.display = 'block';
        if (nv === cf) {
            matchDiv.innerHTML = '<i class="bi bi-check-circle-fill text-success me-1"></i><span class="text-success">Las contraseñas coinciden</span>';
            inputConfirmar.classList.remove('is-invalid');
            inputConfirmar.classList.add('is-valid');
        } else {
            matchDiv.innerHTML = '<i class="bi bi-x-circle-fill text-danger me-1"></i><span class="text-danger">Las contraseñas no coinciden</span>';
            inputConfirmar.classList.remove('is-valid');
            inputConfirmar.classList.add('is-invalid');
        }
    }

    /* ── Habilitar/deshabilitar botón ── */
    function actualizarBoton() {
        const valido = inputNueva.value.length >= 8 && inputNueva.value === inputConfirmar.value;
        if (btnFinal) {
            btnFinal.disabled = !valido;
            btnFinal.style.opacity = valido ? '1' : '0.55';
        }
    }

    inputNueva.addEventListener('input', function () {
        actualizarFortaleza(this.value);
        actualizarMatch();
        actualizarBoton();
    });

    inputConfirmar.addEventListener('input', function () {
        actualizarMatch();
        actualizarBoton();
    });

    /* ── Modal de confirmación ── */
    const modalEl      = document.getElementById('modalConfirmarCambio');
    const btnConfirmar = document.getElementById('btnConfirmarCambio');

    if (btnFinal && modalEl) {
        const modal = new bootstrap.Modal(modalEl);

        btnFinal.addEventListener('click', function () {
            if (inputNueva.value.length < 8 || inputNueva.value !== inputConfirmar.value) return;
            modal.show();
        });

        if (btnConfirmar) {
            btnConfirmar.addEventListener('click', function () {
                this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Cambiando…';
                this.disabled = true;
                modal.hide();
                setTimeout(function () { if (form) form.submit(); }, 280);
            });
        }
    }
});
