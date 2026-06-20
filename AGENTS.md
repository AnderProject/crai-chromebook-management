# CRAI UNEMI — Agent Guide

## Repo structure

```
proyecto_crai/       # Django project config (settings, root urls)
apps/
  prestamos/         # Admin: dashboard, chromebooks, loans, maintenance, reports, settings
  autenticacion/     # Login (estudiante/admin), password reset, support
  estudiantes/       # Student-facing: portal, reservations
templates/
  base.html          # Extends via blocks: titulo, estilos_extra, contenido, scripts_extra, toast_messages
  prestamos/
    _sidebar.html    # Shared sidebar, uses `activo` var
    dashboard.html   # Admin dashboard layout pattern
static/
  css/               # 24 per-page CSS files (all local)
  js/                # 20 per-page JS files (all local)
  fonts/             # Bootstrap Icons font files
```

## Dev commands

```bash
# Activate venv (always needed)
env\Scripts\activate

# Run dev server
python manage.py runserver

# Validate (no tests exist — these are the checks)
python manage.py check
python manage.py makemigrations --check --dry-run

# DB commands
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
```

**No test suite, no linter, no typechecker configured.** Always run `python manage.py check` after changes.

## Architecture

### Layout
- `.dashboard-container` (`height: 100vh; overflow: hidden`) wraps the entire admin
- `.container-fluid` = `calc(100vh - 56px)`, `.row` = `100%`
- `.sidebar-dashboard`: sticky, `height: calc(100vh - 56px)`, self-scrolling
- `.main-content`: `overflow-y: auto` for internal scroll — this is where all page content lives
- **No page-level scrollbar** — all scrolling is inside `.main-content`

### Data model (all tables prefixed `tb_`)
- `auth.User` ← `tb_usuario` (profile, OneToOne) → `tb_estudiante` → `tb_carrera` → `tb_facultad`
- Loan flow: `tb_chromebook` ↔ `tb_prestamo` → `auth.User` / `tb_reserva`
- Supporting: `tb_evidencia`, `tb_mantenimiento`, `tb_notificacion`, `tb_sesion_usuario`, `tb_chatbot_conversacion`
- Students synced from external API carry `origen='api'`, `matricula_id`, `sincronizado`

### External API (matrículas)
- URL: `http://127.0.0.1:8001/api` (override via `API_MATRICULAS_BASE_URL` env var)
- Auth: `X-API-KEY` header (dev key in settings)
- Endpoints: `GET /api/estudiantes/{cedula}/`, `GET /api/estudiantes/` (DRF paginated)
- Sync: `services/sincronizacion.py::sincronizar_estudiante()` (idempotent, creates full chain)
- Two API views in `prestamos/views.py`: `api_test_conexion`, `api_sincronizar_estudiantes`

### Key patterns
- All static assets (Bootstrap 5, Bootstrap Icons, Chart.js) are **local** — no CDN
- Premium reusable button: `.btn-codigo-reservacion` (flex, gradient, icon+text)
- API views use `@csrf_exempt`; page views use `@login_required`
- Context processor `usuario_context` injects `primer_nombre`, `primer_apellido`
- Middleware `RegistrarSesionMiddleware` logs session info per request
- Toast system in `base.html`: reads hidden `#djangoMessages`, rendered by `toast.js`
- **No `.env` file** — dev secrets are hardcoded in `settings.py`

### DB config (dev)
- PostgreSQL: `crai_unemi`, user `postgres`, pass `1508`, port `5432`

## Gotchas
- `detalle_chromebook` view (`prestamos/views.py`) renders `prestamos/chromebooks/detalle.html` — this template does not exist
- Always re-use existing CSS classes (`.btn-codigo-reservacion`, `.tabla-prestamos`) rather than creating new ones for consistency
- When adding new admin pages: include `_sidebar.html` with `activo` var, wrap content in `dashboard-container` > `container-fluid` > `row` > `sidebar` + `main-content`

## Chatbot Architecture (V3 final)

```
Navegador (JS) → POST /estudiantes/api/chatbot/
                          │
                    ┌─────┴──────┐
                    │  Django    │ ← identifica estudiante autenticado
                    │  detecta   │
                    │  keyword?  │
                    └─────┬──────┘
                          │
               ┌──────────┴──────────┐
               │ sí                  │ no
               ▼                     ▼
     Respuesta directa     ┌─────────────────┐
     (disponibilidad,      │ POST a n8n      │
      mis_reservas,        │ con [Usuario:   │
      cancelar)            │  Nombre (Céd)]  │
                           └────────┬────────┘
                                    │
                                    ▼
                     Webhook → Code → AI Agent → Groq
                                         ↓
                              ¿JSON action en output?
                                    │
                         ┌──────────┴──────────┐
                         │ sí                  │ no
                         ▼                     ▼
               Django ejecuta acción    Devuelve respuesta
               (reservar/cancelar/      textual del AI
                mis_reservas)
                         │
                         ▼
               Devuelve confirmación
               al frontend
```

### Cómo funciona
1. **Django `api_chatbot`** (`apps/estudiantes/views.py:245`) recibe el mensaje del estudiante autenticado.
2. **Django primero verifica keywords** (sin llamar a n8n):
   - `disponibilidad` / `disponibles` → consulta BD y responde directo.
   - `mis reservas` / `mis reservaciones` → lista reservas del estudiante.
   - `cancelar [código]` / `anular [código]` → cancela la reserva.
3. Si no es keyword: Django **prefiere** `[Usuario: Nombre (Cédula: X)]` al mensaje y lo envía a n8n.
4. **n8n V3** (`CRAI Chatbot V3`, exportado en `n8n_crai_chatbot_v3.json`): Webhook → **Code** (extrae `data.body.chatInput`) → **AI Agent** (`conversationAgent`, sin tools) → **Groq** (Llama 3.1 8B) → Responder a Webhook.
5. **El AI Agent** puede devolver JSON con acciones:
   - `{"action":"reservar","fecha_uso":"...","hora_inicio":"...","hora_fin":"...","motivo":"..."}`
   - `{"action":"cancelar","codigo":"123456"}`
   - `{"action":"mis_reservas"}`
6. **Django recibe la respuesta** de n8n y busca estos patrones JSON. Si encuentra:
   - `reservar` → crea `tb_reserva` y reemplaza respuesta con confirmación + código.
   - `cancelar` → cambia estado a `cancelada`.
   - `mis_reservas` → consulta BD y lista reservas.

### Sistema híbrido (sin tools en n8n)
- Llama 3.1 8B no ejecuta tools de forma confiable con ToolHttpRequest de n8n.
- **Solución**: Django maneja TODA la lógica de negocio. n8n solo conversa.
- Keywords comunes jamás tocan n8n → más rápido y confiable.

### Conexiones n8n correctas
- **Webhook → main → Code**
- **Code → main → AI Agent**
- **AI Agent → main → Responder a Webhook**
- **Groq Chat Model → ai_languageModel → AI Agent** (el sub-nodo se conecta AL padre, no al revés)
- `agent: "conversationAgent"` (sin tools, no `toolsAgent`)

### Endpoints Django auxiliares (solo debug/testing)
- `GET /estudiantes/api/info-estudiante/?cedula=X`
- `GET /estudiantes/api/disponibilidad/`
- `GET /estudiantes/api/mis-reservas/?cedula=X`
- `POST /estudiantes/api/crear-reserva/`
