# CRAI UNEMI — Guía de instalación (clonar y arrancar)

Sistema de reservas y préstamos de Chromebooks del CRAI (Django 5 + PostgreSQL).
Esta guía deja el proyecto funcionando en una máquina nueva tras clonar el repositorio.

---

## 1. Requisitos previos

Instala esto **antes** de ejecutar el instalador:

| Programa | Versión | Notas |
|----------|---------|-------|
| **Python** | 3.10 o superior | Al instalar, marca **"Add Python to PATH"**. Verifica con `python --version`. |
| **PostgreSQL** | 14 o superior | Anota la contraseña del usuario `postgres` que defines durante la instalación. Verifica que el servicio esté corriendo. |
| **Git** | cualquiera | Para clonar el repositorio. |

> El chatbot (n8n) y el túnel (ngrok) son **opcionales** y solo hacen falta para
> probar el bot de reservas / WhatsApp. El sistema arranca y funciona sin ellos.

---

## 2. Clonar el repositorio

```bash
git clone <URL-DEL-REPOSITORIO> proyecto_crai
cd proyecto_crai
```

---

## 3. Instalación automática (recomendado)

Haz **doble clic** en:

```
instalar_crai.bat
```

El instalador hace todo por ti:

1. Crea el entorno virtual `env\`.
2. Instala las dependencias de `requirements.txt`.
3. Crea el archivo `.env` y **genera una `SECRET_KEY` nueva** automáticamente.
4. Crea la base de datos PostgreSQL `crai_unemi` (si no existe).
5. Aplica las migraciones.
6. Carga los datos de demostración (`datos_demo.json`: estudiantes, inventario, etc.).
7. Te ofrece crear un superusuario para el panel `/admin`.

### Único ajuste manual: la contraseña de PostgreSQL

Cuando el instalador prepara el `.env`, te preguntará si quieres **pausar para
editarlo**. Responde **S** y, en el `.env` que se abre, cambia esta línea por la
contraseña de **tu** usuario `postgres`:

```env
DB_PASSWORD=1508
```

Guarda, cierra el Bloc de notas y el instalador continuará creando la base de datos.

> Si tu usuario/host/puerto de PostgreSQL son distintos, ajusta también
> `DB_USER`, `DB_HOST` y `DB_PORT`.

---

## 4. Arrancar el sistema

Una vez instalado, para usar el sistema haz doble clic en:

```
iniciar_crai.bat
```

Levanta en ventanas separadas:

- **Django** → http://localhost:8000 (portal) y http://localhost:8000/admin
- **ngrok** → túnel público (solo si tienes ngrok configurado; opcional)
- **n8n** → http://localhost:5678 (chatbot; opcional)

Para arrancar **solo Django** sin el chatbot ni el túnel:

```bash
env\Scripts\python.exe manage.py runserver
```

---

## 5. Instalación manual (si el .bat falla)

```bash
:: 1) Entorno virtual
python -m venv env
env\Scripts\activate

:: 2) Dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 3) Archivo .env (copiar plantilla y editar)
copy .env.example .env
::   -> edita .env: pon tu DB_PASSWORD y genera una SECRET_KEY con:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

:: 4) Crear la base de datos en PostgreSQL
::   (desde psql o pgAdmin)  CREATE DATABASE crai_unemi;

:: 5) Migraciones + datos de demo
python manage.py migrate
python manage.py loaddata datos_demo.json

:: 6) Superusuario (opcional)
python manage.py createsuperuser
```

---

## 6. Variables de entorno (`.env`)

Todas las variables están documentadas en **`.env.example`**. Las imprescindibles:

| Variable | Para qué sirve | ¿Obligatoria? |
|----------|----------------|----------------|
| `SECRET_KEY` | Clave de Django | Sí (la genera el instalador) |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | Conexión a PostgreSQL | Sí |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Recuperación de contraseña por correo (Gmail App Password) | No (solo esa función) |
| `KIOSKO_API_KEY` | App kiosko de los Chromebooks | No |
| `WHATSAPP_*` | Chatbot por WhatsApp | No |
| `API_MATRICULAS_*` | API externa de matrículas | No (con datos de demo no hace falta) |

> El `.env` **nunca** se sube al repositorio (está en `.gitignore`). Cada persona
> tiene el suyo.

---

## 7. Problemas frecuentes

- **`fe_sendauth: no password supplied` / `password authentication failed`**
  → La contraseña en `DB_PASSWORD` no coincide con tu usuario `postgres`. Corrígela en `.env`.

- **`could not connect to server` / `Connection refused`**
  → El servicio de PostgreSQL no está corriendo. Inícialo (Servicios de Windows → `postgresql-x64-*`).

- **`RuntimeError: Falta SECRET_KEY`**
  → No existe `.env` o la línea `SECRET_KEY=` está vacía. Ejecuta de nuevo `instalar_crai.bat`.

- **`python no se reconoce como comando`**
  → Python no está en el PATH. Reinstálalo marcando "Add Python to PATH".
