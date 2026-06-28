@echo off
REM ============================================================
REM   CRAI UNEMI - Arranque de servicios (un solo clic)
REM   Levanta Django (8000), ngrok (dominio fijo -> 8000) y n8n (5678)
REM   Cada servicio abre en su propia ventana. Cierra la ventana
REM   correspondiente para detener ese servicio.
REM ============================================================

REM Ubicarse en la carpeta del proyecto (donde esta este .bat)
cd /d "%~dp0"

echo.
echo  =====================================================
echo   Iniciando servicios CRAI...
echo   - Django : http://localhost:8000
echo   - ngrok  : https://immunize-bronco-graveyard.ngrok-free.dev
echo   - n8n    : http://localhost:5678
echo  =====================================================
echo.

REM ---- 1) n8n (tarda en arrancar, se lanza primero) ----
start "n8n CRAI :5678" cmd /k "npx n8n"

REM ---- 2) Django en 0.0.0.0:8000 ----
start "Django CRAI :8000" cmd /k "env\Scripts\python.exe manage.py runserver 0.0.0.0:8000"

REM ---- Pequena espera para que Django levante antes del tunel ----
timeout /t 3 /nobreak >nul

REM ---- 3) ngrok con dominio fijo apuntando al 8000 ----
start "ngrok CRAI :8000" cmd /k "ngrok http --domain=immunize-bronco-graveyard.ngrok-free.dev 8000"

echo.
echo  Servicios lanzados en ventanas separadas.
echo  Puedes cerrar ESTA ventana; las otras seguiran corriendo.
echo.
timeout /t 4 /nobreak >nul
