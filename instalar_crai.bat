@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
REM ============================================================
REM   CRAI UNEMI - Instalador (primer arranque tras clonar)
REM   Deja el proyecto listo para usarse:
REM     1) Crea el entorno virtual (env\)
REM     2) Instala las dependencias (requirements.txt)
REM     3) Crea el .env y genera la SECRET_KEY
REM     4) Crea la base de datos PostgreSQL (si no existe)
REM     5) Aplica las migraciones
REM     6) Carga los datos de demo (datos_demo.json)
REM     7) (Opcional) crea un superusuario
REM
REM   Requisitos previos (ver README_INSTALACION.md):
REM     - Python 3.10+ en el PATH
REM     - PostgreSQL instalado y corriendo
REM ============================================================

cd /d "%~dp0"

echo.
echo  =====================================================
echo    INSTALADOR CRAI UNEMI
echo  =====================================================
echo.

REM ---- 0) Detectar Python -------------------------------------------------
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo  [ERROR] No se encontro Python en el PATH.
    echo          Instala Python 3.10+ desde https://www.python.org/downloads/
    echo          y marca la casilla "Add Python to PATH".
    goto :fin_error
)
echo  Python detectado:
%PY% --version

REM ---- 1) Crear entorno virtual ------------------------------------------
echo.
echo  [1/6] Preparando entorno virtual (env\)...
if exist "env\Scripts\python.exe" (
    echo        El entorno virtual ya existe: se reutiliza.
) else (
    %PY% -m venv env
    if errorlevel 1 (
        echo  [ERROR] No se pudo crear el entorno virtual.
        goto :fin_error
    )
    echo        Entorno virtual creado.
)
set "VENV_PY=env\Scripts\python.exe"

REM ---- 2) Instalar dependencias -----------------------------------------
echo.
echo  [2/6] Instalando dependencias (puede tardar unos minutos)...
"%VENV_PY%" -m pip install --upgrade pip >nul
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo  [ERROR] Fallo la instalacion de dependencias.
    goto :fin_error
)
echo        Dependencias instaladas.

REM ---- 3) Preparar .env + SECRET_KEY + base de datos --------------------
echo.
echo  [3/6] Preparando .env y base de datos...
set "PYTHONUTF8=1"
"%VENV_PY%" scripts\preparar_entorno.py
echo.
echo        ^>^> Si vas a usar TU propia contraseña de PostgreSQL,
echo           abre el archivo .env y ajusta DB_PASSWORD antes de continuar.
echo.
choice /c SN /n /m "        Pausar para editar el .env ahora? (S/N): "
if errorlevel 2 goto :tras_env
notepad .env
echo        Reintentando creacion de la base de datos con el .env actualizado...
"%VENV_PY%" scripts\preparar_entorno.py
:tras_env

REM ---- 4) Migraciones ----------------------------------------------------
echo.
echo  [4/6] Aplicando migraciones...
"%VENV_PY%" manage.py migrate
if errorlevel 1 (
    echo  [ERROR] Fallaron las migraciones. Suele ser un problema de conexion
    echo          con PostgreSQL. Revisa DB_PASSWORD en el .env y que el servicio
    echo          de PostgreSQL este corriendo. Luego vuelve a ejecutar este .bat.
    goto :fin_error
)
echo        Migraciones aplicadas.

REM ---- 5) Datos de demo --------------------------------------------------
echo.
echo  [5/6] Cargando datos de demostracion...
if exist "datos_demo.json" (
    choice /c SN /n /m "        Cargar datos_demo.json con estudiantes, inventario, etc.? S/N: "
    if errorlevel 2 (
        echo        Omitido. Empezaras con la base vacia.
    ) else (
        "%VENV_PY%" manage.py loaddata datos_demo.json
        if errorlevel 1 (
            echo  [AVISO] No se pudieron cargar los datos de demo.
        ) else (
            echo        Datos de demo cargados.
        )
    )
) else (
    echo        No se encontro datos_demo.json: se omite.
)

REM ---- 6) Superusuario ---------------------------------------------------
echo.
echo  [6/6] Cuenta de administrador de Django (/admin)...
choice /c SN /n /m "        Crear un superusuario ahora? (S/N): "
if errorlevel 2 (
    echo        Omitido. Puedes crearlo luego con:
    echo            env\Scripts\python.exe manage.py createsuperuser
) else (
    "%VENV_PY%" manage.py createsuperuser
)

echo.
echo  =====================================================
echo    INSTALACION COMPLETADA
echo  =====================================================
echo.
echo    Para arrancar el sistema usa:  iniciar_crai.bat
echo    (o solo Django:  env\Scripts\python.exe manage.py runserver)
echo.
echo    Portal:  http://localhost:8000
echo    Admin :  http://localhost:8000/admin
echo.
pause
exit /b 0

:fin_error
echo.
echo  La instalacion se detuvo por un error. Corrige lo indicado y vuelve a
echo  ejecutar instalar_crai.bat.
echo.
pause
exit /b 1
