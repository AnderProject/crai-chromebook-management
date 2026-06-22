// =============================================
// DESARROLLADORES - CRAI UNEMI
//  1) Respaldo de fotos: si una imagen no existe, se oculta
//     y se muestra un ícono de persona (tarjetas y modales).
//  2) Modal tipo portafolio por cada desarrollador.
// =============================================

(function () {
    document.addEventListener('DOMContentLoaded', function () {

        // ---- 1) Respaldo de fotos (tarjetas y modales) ----
        document.querySelectorAll('.dev-foto-img, .dev-modal-foto-img').forEach(function (img) {
            var aplicarFallback = function () {
                img.style.display = 'none';
                var fb = img.parentElement.querySelector('.dev-foto-fallback, .dev-modal-foto-fallback');
                if (fb) { fb.style.display = 'flex'; }
            };
            img.addEventListener('error', aplicarFallback);
            // por si la imagen ya falló antes de registrar el listener
            if (img.complete && img.naturalWidth === 0) { aplicarFallback(); }
        });

        // ---- 2) Modales de portafolio ----
        var abierto = null;

        function abrir(modal) {
            if (!modal) { return; }
            abierto = modal;
            modal.classList.add('abierto');
            modal.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
            var cerrar = modal.querySelector('[data-dev-close]');
            if (cerrar) { cerrar.focus(); }
        }

        function cerrar() {
            if (!abierto) { return; }
            abierto.classList.remove('abierto');
            abierto.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
            abierto = null;
        }

        // Abrir desde cada tarjeta
        document.querySelectorAll('.dev-card[data-dev]').forEach(function (card) {
            card.addEventListener('click', function () {
                abrir(document.getElementById('modal-' + card.dataset.dev));
            });
        });

        // Botón de cierre (X)
        document.querySelectorAll('[data-dev-close]').forEach(function (btn) {
            btn.addEventListener('click', cerrar);
        });

        // Cerrar al hacer clic en el fondo oscuro
        document.querySelectorAll('.dev-modal-overlay').forEach(function (ov) {
            ov.addEventListener('click', function (e) {
                if (e.target === ov) { cerrar(); }
            });
        });

        // Cerrar con la tecla Escape
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && abierto) { cerrar(); }
        });
    });
})();
