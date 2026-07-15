@echo off
REM ============================================================
REM   CRAI UNEMI - Arranque de servicios (un solo clic)
REM   Abre TODO en UNA sola ventana de Windows Terminal, en pestanas:
REM     - Django del sistema / Chromebooks : 0.0.0.0:8000
REM     - ngrok (tunel dominio fijo -> 8000)
REM     - n8n : 5678
REM     - API de matriculas : 8001   (proyecto aparte)
REM   Cierra la pestana correspondiente para detener ese servicio.
REM ============================================================

REM Carpeta de este proyecto (sin la barra final, para que -d no falle)
set "PROY=%~dp0"
if "%PROY:~-1%"=="\" set "PROY=%PROY:~0,-1%"

REM Carpeta del proyecto de la API de matriculas (hermana de este proyecto).
REM Ruta RELATIVA: funciona este donde este la carpeta padre, siempre que
REM proyecto_crai y api_matriculas_unemi esten juntas en el mismo nivel.
for %%I in ("%~dp0..\api_matriculas_unemi") do set "MATRIC=%%~fI"

echo.
echo  =====================================================
echo   Iniciando servicios CRAI...
echo   - Django : http://localhost:8000
echo   - ngrok  : https://immunize-bronco-graveyard.ngrok-free.dev
echo   - n8n    : http://localhost:5678
echo   - API Matriculas : http://localhost:8001
echo  =====================================================
echo.

REM Si existe Windows Terminal (wt), todo va en PESTANAS de una sola ventana.
where wt >nul 2>nul
if %errorlevel%==0 goto WT

REM ---------- Fallback: ventanas separadas (sin Windows Terminal) ----------
start "n8n CRAI :5678" cmd /k "n8n start"
start "Django CRAI :8000" cmd /k "cd /d %PROY% && env\Scripts\python.exe manage.py runserver 0.0.0.0:8000"
timeout /t 3 /nobreak >nul
start "ngrok CRAI :8000" cmd /k "ngrok http --domain=immunize-bronco-graveyard.ngrok-free.dev 8000"
start "API Matriculas :8001" cmd /k "cd /d %MATRIC% && env\Scripts\python.exe manage.py runserver 8001"
goto END

:WT
REM ---------- Windows Terminal: una ventana ("crai"), varias pestanas ----------
REM La 1ra crea la ventana; las demas se agregan como pestanas a esa misma ventana.
wt -w crai new-tab -d "%PROY%" --title "Django :8000" cmd /k "env\Scripts\python.exe manage.py runserver 0.0.0.0:8000"
timeout /t 2 /nobreak >nul
wt -w crai new-tab -d "%PROY%" --title "ngrok :8000" cmd /k "ngrok http --domain=immunize-bronco-graveyard.ngrok-free.dev 8000"
timeout /t 1 /nobreak >nul
wt -w crai new-tab -d "%PROY%" --title "n8n :5678" cmd /k "n8n start"
timeout /t 1 /nobreak >nul
wt -w crai new-tab -d "%MATRIC%" --title "API Matriculas :8001" cmd /k "env\Scripts\python.exe manage.py runserver 8001"

:END
