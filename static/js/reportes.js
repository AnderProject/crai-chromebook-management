/* ============================================================
   REPORTES - CRAI UNEMI
   Construye los gráficos del apartado de reportes con Chart.js.
   Los datos llegan desde la vista mediante {{ ... |json_script }} en la
   plantilla; aquí solo se leen y se dibujan. Nada de datos quemados.
   ============================================================ */

(function () {
    'use strict';

    // Paleta alineada al diseño del sistema (dashboard.css)
    const COLOR = {
        primario: '#1a237e',
        azul: '#4285f4',
        naranja: '#ff6f00',
        cyan: '#00acc1',
        verde: '#34a853',
        rojo: '#ea4335',
        gris: '#9e9e9e',
        morado: '#7e57c2',
    };

    // Paleta cíclica para gráficos con número variable de categorías
    const PALETA = [
        COLOR.azul, COLOR.naranja, COLOR.verde, COLOR.cyan,
        COLOR.morado, COLOR.rojo, COLOR.primario, COLOR.gris,
    ];

    function colores(n) {
        const out = [];
        for (let i = 0; i < n; i++) out.push(PALETA[i % PALETA.length]);
        return out;
    }

    function leerJSON(id) {
        const el = document.getElementById(id);
        if (!el) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return null;
        }
    }

    function sinDatos(data) {
        if (!Array.isArray(data) || data.length === 0) return true;
        return data.every((n) => !n);
    }

    /* Si no hay datos, oculta el canvas y muestra el mensaje de "sin datos". */
    function manejarVacio(canvasId, data) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return true;
        if (sinDatos(data)) {
            const wrap = canvas.closest('.reporte-canvas-wrap');
            if (wrap) {
                wrap.innerHTML =
                    '<div class="reporte-vacio">' +
                    '<i class="bi bi-bar-chart-line"></i>' +
                    '<span>Sin datos para mostrar</span>' +
                    '</div>';
            }
            return true;
        }
        return false;
    }

    const graficos = [];

    function crearGrafico(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        graficos.push(new Chart(canvas.getContext('2d'), config));
    }

    function opcionesBase(extra) {
        const base = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { font: { family: "'Segoe UI', sans-serif" }, padding: 12 },
                },
            },
        };
        return Object.assign(base, extra || {});
    }

    // Helpers para los tipos de gráfico más repetidos
    function barras(canvasId, dataId, labelsId, etiqueta, opts) {
        const labels = leerJSON(labelsId) || [];
        const data = leerJSON(dataId) || [];
        if (manejarVacio(canvasId, data)) return;
        const config = {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: etiqueta,
                    data: data,
                    backgroundColor: (opts && opts.color) || COLOR.azul,
                    borderRadius: 6,
                }],
            },
            options: opcionesBase(Object.assign({
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
            }, (opts && opts.options) || {})),
        };
        crearGrafico(canvasId, config);
    }

    function linea(canvasId, dataId, labelsId, etiqueta, color) {
        const labels = leerJSON(labelsId) || [];
        const data = leerJSON(dataId) || [];
        if (manejarVacio(canvasId, data)) return;
        crearGrafico(canvasId, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: etiqueta,
                    data: data,
                    borderColor: color || COLOR.primario,
                    backgroundColor: 'rgba(26, 35, 126, 0.12)',
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: color || COLOR.primario,
                    pointRadius: 3,
                }],
            },
            options: opcionesBase({
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
            }),
        });
    }

    function circular(canvasId, dataId, labels, paleta, tipo) {
        const data = leerJSON(dataId) || [];
        if (manejarVacio(canvasId, data)) return;
        crearGrafico(canvasId, {
            type: tipo || 'doughnut',
            data: {
                labels: labels,
                datasets: [{ data: data, backgroundColor: paleta, borderWidth: 0 }],
            },
            options: opcionesBase(tipo === 'pie' ? {} : { cutout: '60%' }),
        });
    }

    function circularDinamico(canvasId, dataId, labelsId, tipo) {
        const labels = leerJSON(labelsId) || [];
        const data = leerJSON(dataId) || [];
        if (manejarVacio(canvasId, data)) return;
        crearGrafico(canvasId, {
            type: tipo || 'pie',
            data: {
                labels: labels,
                datasets: [{ data: data, backgroundColor: colores(data.length), borderWidth: 0 }],
            },
            options: opcionesBase(tipo === 'doughnut' ? { cutout: '60%' } : {}),
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (typeof Chart === 'undefined') {
            console.error('Chart.js no se cargó.');
            return;
        }

        Chart.defaults.color = '#6c757d';
        Chart.defaults.font.family = "'Segoe UI', sans-serif";

        // ---- TEMPORAL ----
        barras('chartPorMes', 'data-mes-data', 'data-mes-labels', 'Préstamos', { color: COLOR.primario });
        linea('chartPorSemana', 'data-semana-data', 'data-semana-labels', 'Préstamos', COLOR.azul);
        linea('chartHorasPico', 'data-hora-data', 'data-hora-labels', 'Préstamos', COLOR.naranja);
        barras('chartPorDia', 'data-dia-data', 'data-dia-labels', 'Préstamos', { color: COLOR.cyan });

        // ---- DISTRIBUCIÓN ----
        barras('chartCarrera', 'data-carrera-data', 'data-carrera-labels', 'Préstamos', {
            color: COLOR.azul,
            options: { indexAxis: 'y', scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } },
        });
        circular('chartInventario', 'data-inventario-data',
            ['Disponibles', 'Prestados', 'Mantenimiento'],
            [COLOR.verde, COLOR.azul, COLOR.naranja], 'doughnut');
        barras('chartSemestre', 'data-semestre-data', 'data-semestre-labels', 'Préstamos', { color: COLOR.morado });
        barras('chartFacultad', 'data-facultad-data', 'data-facultad-labels', 'Préstamos', { color: COLOR.cyan });
        circular('chartCondicion', 'data-condicion-data',
            ['Bueno', 'Regular', 'Malo'],
            [COLOR.verde, COLOR.naranja, COLOR.rojo], 'pie');
        circularDinamico('chartMarca', 'data-marca-data', 'data-marca-labels', 'pie');

        // ---- MANTENIMIENTO ----
        barras('chartMantMes', 'data-mant-mes-data', 'data-mant-mes-labels', 'Mantenimientos', { color: COLOR.naranja });
        circular('chartMantTipo', 'data-mant-tipo-data',
            ['Preventivo', 'Correctivo'],
            [COLOR.verde, COLOR.rojo], 'doughnut');

        // Chart.js no calcula bien el tamaño en pestañas ocultas (quedan en 0px).
        // Al mostrarse una pestaña, redimensionamos todos los gráficos.
        document.querySelectorAll('#reporteTabs button[data-bs-toggle="tab"]').forEach(function (btn) {
            btn.addEventListener('shown.bs.tab', function () {
                graficos.forEach(function (g) { g.resize(); });
            });
        });
    });
})();
