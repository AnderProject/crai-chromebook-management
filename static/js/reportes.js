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

    // Aclara un color hex mezclándolo con blanco (para los degradados).
    function aclarar(hex, amt) {
        const h = hex.replace('#', '');
        const r = parseInt(h.substring(0, 2), 16);
        const g = parseInt(h.substring(2, 4), 16);
        const b = parseInt(h.substring(4, 6), 16);
        const m = (c) => Math.round(c + (255 - c) * amt);
        return 'rgb(' + m(r) + ',' + m(g) + ',' + m(b) + ')';
    }

    // Degradado vertical para las barras (arriba más claro → base al fondo).
    function degradadoBarra(base) {
        return function (context) {
            const chart = context.chart;
            const area = chart.chartArea;
            if (!area) return base;
            const g = chart.ctx.createLinearGradient(0, area.top, 0, area.bottom);
            g.addColorStop(0, aclarar(base, 0.35));
            g.addColorStop(1, base);
            return g;
        };
    }

    // Sombra suave bajo barras/arcos/líneas (estilo Office, sin 3D que distorsione).
    const sombraPlugin = {
        id: 'sombraSuave',
        beforeDatasetsDraw(chart) {
            const ctx = chart.ctx;
            ctx.save();
            ctx.shadowColor = 'rgba(20, 40, 80, 0.20)';
            ctx.shadowBlur = 9;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 4;
        },
        afterDatasetsDraw(chart) { chart.ctx.restore(); },
    };

    // Acorta nombres largos (p.ej. facultades) para que no desborden el gráfico.
    function acortar(label, max) {
        if (typeof label !== 'string') return label;
        let t = label.replace(/^Facultad de (la |los |las )?/i, '').trim();
        t = t.replace('Educación Comercial y Derecho', 'y Derecho')
             .replace('Servicios Sociales', 'S. Sociales')
             .replace('Ciencias Sociales', 'C. Sociales');
        if (t.length > (max || 22)) t = t.substring(0, (max || 22) - 1).trim() + '…';
        return t;
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
    const graficoPorCanvas = {};

    function crearGrafico(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const g = new Chart(canvas.getContext('2d'), config);
        graficos.push(g);
        graficoPorCanvas[canvasId] = g;
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
        const base = (opts && opts.color) || COLOR.azul;
        const config = {
            type: 'bar',
            data: {
                labels: (opts && opts.acortarLabels) ? labels.map((l) => acortar(l, 20)) : labels,
                datasets: [{
                    label: etiqueta,
                    data: data,
                    backgroundColor: degradadoBarra(base),
                    hoverBackgroundColor: base,
                    borderRadius: 8,
                    borderSkipped: false,
                    maxBarThickness: 46,
                }],
            },
            options: opcionesBase(Object.assign({
                plugins: {
                    legend: { display: false },
                    tooltip: (opts && opts.labelsCompletos)
                        ? { callbacks: { title: (items) => (labels[items[0].dataIndex] || '') } }
                        : {},
                },
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

    // ---- Gráfico temporal interactivo (Día / Semana / Mes / Año) ----
    let chartTemporal = null;

    function pintarTemporal(rango) {
        fetch('/prestamos/api/reportes-temporal/?rango=' + rango, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                const canvas = document.getElementById('chartTemporal');
                if (!canvas) return;
                if (chartTemporal) {
                    chartTemporal.data.labels = d.labels;
                    chartTemporal.data.datasets[0].data = d.data;
                    chartTemporal.update();
                } else {
                    chartTemporal = new Chart(canvas.getContext('2d'), {
                        type: 'line',
                        data: {
                            labels: d.labels,
                            datasets: [{
                                label: d.etiqueta || 'Préstamos',
                                data: d.data,
                                borderColor: COLOR.primario,
                                backgroundColor: 'rgba(26, 35, 126, 0.12)',
                                fill: true,
                                tension: 0.35,
                                pointRadius: 3,
                                pointBackgroundColor: COLOR.primario,
                            }],
                        },
                        options: opcionesBase({
                            plugins: { legend: { display: false } },
                            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
                        }),
                    });
                }
            })
            .catch(function () { /* silencioso */ });
    }

    function inicializarTemporal() {
        const cont = document.getElementById('reporteRango');
        if (!cont) return;
        cont.querySelectorAll('.reporte-rango-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                cont.querySelectorAll('.reporte-rango-btn').forEach(function (b) {
                    b.classList.remove('active');
                });
                btn.classList.add('active');
                pintarTemporal(btn.getAttribute('data-rango'));
            });
        });
        pintarTemporal('semana'); // rango por defecto (coincide con el botón activo)
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (typeof Chart === 'undefined') {
            console.error('Chart.js no se cargó.');
            return;
        }

        Chart.defaults.color = '#6c757d';
        Chart.defaults.font.family = "'Segoe UI', sans-serif";
        Chart.register(sombraPlugin);   // sombra suave en todos los gráficos

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
        // Facultad: barras HORIZONTALES + nombres acortados (los largos desbordaban);
        // el tooltip muestra el nombre completo.
        barras('chartFacultad', 'data-facultad-data', 'data-facultad-labels', 'Préstamos', {
            color: COLOR.cyan,
            acortarLabels: true,
            labelsCompletos: true,
            options: { indexAxis: 'y', scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } },
        });
        circular('chartCondicion', 'data-condicion-data',
            ['Bueno', 'Regular', 'Malo'],
            [COLOR.verde, COLOR.naranja, COLOR.rojo], 'pie');
        circularDinamico('chartMarca', 'data-marca-data', 'data-marca-labels', 'pie');

        // ---- TEMPORAL INTERACTIVO ----
        inicializarTemporal();

        // ---- MANTENIMIENTO ----
        barras('chartMantMes', 'data-mant-mes-data', 'data-mant-mes-labels', 'Mantenimientos', { color: COLOR.naranja });
        circular('chartMantTipo', 'data-mant-tipo-data',
            ['Preventivo', 'Correctivo'],
            [COLOR.verde, COLOR.rojo], 'doughnut');

        // Botón de descarga (PNG) en cada tarjeta con gráfico.
        agregarExportacion();

        // Chart.js no calcula bien el tamaño en pestañas ocultas (quedan en 0px).
        // Al mostrarse una pestaña, redimensionamos todos los gráficos.
        document.querySelectorAll('#reporteTabs button[data-bs-toggle="tab"]').forEach(function (btn) {
            btn.addEventListener('shown.bs.tab', function () {
                graficos.forEach(function (g) { g.resize(); });
            });
        });
    });

    // ---- Exportar cada gráfico como imagen PNG (fondo blanco) ----
    function descargarGrafico(canvas, nombre) {
        const chart = Chart.getChart(canvas);
        if (!chart) return;
        const src = chart.canvas;
        const tmp = document.createElement('canvas');
        tmp.width = src.width;
        tmp.height = src.height;
        const c = tmp.getContext('2d');
        c.fillStyle = '#ffffff';
        c.fillRect(0, 0, tmp.width, tmp.height);
        c.drawImage(src, 0, 0);
        const a = document.createElement('a');
        a.href = tmp.toDataURL('image/png');
        a.download = 'reporte_' + (nombre || 'grafico').replace(/[^\wáéíóúñ-]+/gi, '_').toLowerCase() + '.png';
        document.body.appendChild(a);
        a.click();
        a.remove();
    }

    function agregarExportacion() {
        document.querySelectorAll('.reporte-card').forEach(function (card) {
            const canvas = card.querySelector('canvas');
            const header = card.querySelector('.reporte-card-header');
            if (!canvas || !header || header.querySelector('.reporte-export')) return;
            const h5 = header.querySelector('h5');
            const titulo = h5 ? h5.textContent.trim() : 'grafico';
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'reporte-export';
            btn.title = 'Descargar como imagen';
            btn.innerHTML = '<i class="bi bi-download"></i>';
            btn.addEventListener('click', function () { descargarGrafico(canvas, titulo); });
            header.appendChild(btn);
        });
    }
})();
