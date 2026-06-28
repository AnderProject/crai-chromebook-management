"""
Ayudante del instalador (instalar_crai.bat).

1. Crea el archivo .env a partir de .env.example si no existe.
2. Genera una SECRET_KEY de Django nueva si todavía es el valor de ejemplo.
3. Crea la base de datos PostgreSQL (DB_NAME) si aún no existe, usando psycopg2
   y los datos de conexión definidos en el .env.

No detiene la instalación si la base de datos falla: solo muestra un aviso, ya
que el paso de migraciones revelará el error de conexión con más detalle.

Uso:  python scripts/preparar_entorno.py
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV = BASE_DIR / '.env'
ENV_EXAMPLE = BASE_DIR / '.env.example'


def crear_env():
    """Crea .env desde la plantilla si no existe."""
    if ENV.exists():
        print('  .env ya existe: se conserva tal cual.')
        return
    if not ENV_EXAMPLE.exists():
        print('  [ERROR] No se encontro .env.example; no puedo crear el .env.')
        sys.exit(1)
    ENV.write_text(ENV_EXAMPLE.read_text(encoding='utf-8'), encoding='utf-8')
    print('  .env creado a partir de .env.example.')


def asegurar_secret_key():
    """Reemplaza la SECRET_KEY de ejemplo por una generada al azar."""
    from django.core.management.utils import get_random_secret_key

    texto = ENV.read_text(encoding='utf-8')
    lineas = texto.splitlines()
    cambiado = False
    placeholders = ('cambia-esto-por-una-clave-secreta', '')
    for i, linea in enumerate(lineas):
        if linea.startswith('SECRET_KEY='):
            valor = linea.split('=', 1)[1].strip()
            if valor in placeholders:
                lineas[i] = 'SECRET_KEY=' + get_random_secret_key()
                cambiado = True
            break
    if cambiado:
        ENV.write_text('\n'.join(lineas) + '\n', encoding='utf-8')
        print('  SECRET_KEY generada y guardada en .env.')
    else:
        print('  SECRET_KEY ya estaba definida: se conserva.')


def crear_base_de_datos():
    """Crea la base de datos en PostgreSQL si no existe (usando psycopg2)."""
    from dotenv import dotenv_values

    cfg = dotenv_values(ENV)
    nombre = cfg.get('DB_NAME') or 'crai_unemi'
    usuario = cfg.get('DB_USER') or 'postgres'
    clave = cfg.get('DB_PASSWORD') or ''
    host = cfg.get('DB_HOST') or 'localhost'
    puerto = cfg.get('DB_PORT') or '5432'

    try:
        import psycopg2
        from psycopg2 import sql
    except ImportError:
        print('  [AVISO] psycopg2 no esta instalado todavia; omito crear la BD.')
        return

    try:
        # Conectamos a la base 'postgres' (siempre existe) para poder crear la nuestra.
        conn = psycopg2.connect(dbname='postgres', user=usuario, password=clave,
                                host=host, port=puerto)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', (nombre,))
            if cur.fetchone():
                print(f'  La base de datos "{nombre}" ya existe.')
            else:
                cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(nombre)))
                print(f'  Base de datos "{nombre}" creada.')
        conn.close()
    except Exception as exc:  # noqa: BLE001 - queremos avisar de cualquier fallo
        print('  [AVISO] No se pudo crear/verificar la base de datos automaticamente:')
        print(f'          {exc}')
        print('  Revisa que PostgreSQL este corriendo y que DB_USER/DB_PASSWORD del')
        print('  archivo .env sean correctos. Luego vuelve a ejecutar el instalador.')


if __name__ == '__main__':
    print('[1/3] Preparando archivo .env...')
    crear_env()
    print('[2/3] Verificando SECRET_KEY...')
    asegurar_secret_key()
    print('[3/3] Verificando base de datos PostgreSQL...')
    crear_base_de_datos()
    print('Entorno preparado.')
