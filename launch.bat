@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================================
REM  launch.bat - Launcher Windows para app PySide6 (Horas Sindicales)
REM  - Crea/usa .venv
REM  - Instala dependencias desde requirements.txt
REM  - Ejecuta main.py
REM  - Mensajes en español + manejo de errores
REM
REM  Dependencias esperadas en requirements.txt (referencia):
REM    PySide6
REM    reportlab
REM    openpyxl
REM    gspread
REM    google-api-python-client
REM    python-dotenv
REM
REM  Recursos del proyecto:
REM    - main.py
REM    - requirements.txt
REM    - logo.png  (logo usado también en UI / PDF)
REM    - BD SQLite (horas.db o similar)
REM ==========================================================

REM 1) Ir al directorio del launcher (raíz del proyecto)
cd /d "%~dp0"

echo.
echo ============================================
echo  Lanzador Horas Sindicales (PySide6)
echo ============================================
echo.

REM 2) Comprobaciones básicas de archivos
if not exist "main.py" (
  echo [ERROR] No se encuentra main.py en la carpeta actual:
  echo         %CD%
  echo         Asegurate de ejecutar este .bat desde la raiz del proyecto.
  echo.
  pause
  exit /b 1
)

if not exist "requirements.txt" (
  echo [ERROR] No se encuentra requirements.txt en la carpeta actual:
  echo         %CD%
  echo.
  pause
  exit /b 1
)

REM 3) Detectar Python
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] No se encuentra "python" en PATH.
  echo         Instala Python 3.11+ y marca "Add Python to PATH".
  echo         Alternativa: ejecuta desde un terminal donde python funcione.
  echo.
  pause
  exit /b 1
)

REM 4) Crear venv si no existe
if not exist ".venv" (
  echo [INFO] No existe .venv. Creando entorno virtual...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Fallo creando el entorno virtual (.venv).
    echo         Revisa permisos / instalacion de Python.
    echo.
    pause
    exit /b 1
  )
) else (
  echo [INFO] Entorno virtual encontrado: .venv
)

REM 5) Resolver ejecutable python del venv (sin activar)
set "VENV_PY=%CD%\.venv\Scripts\python.exe"
set "VENV_PIP=%CD%\.venv\Scripts\pip.exe"

if not exist "%VENV_PY%" (
  echo [ERROR] No se encuentra el Python del entorno virtual:
  echo         %VENV_PY%
  echo         Borra .venv y vuelve a ejecutar el launcher.
  echo.
  pause
  exit /b 1
)

REM 6) Actualizar pip e instalar dependencias
echo.
echo [INFO] Actualizando pip...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] No se pudo actualizar pip.
  echo.
  pause
  exit /b 1
)

echo.
echo [INFO] Instalando/Verificando dependencias desde requirements.txt...
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Fallo instalando dependencias.
  echo         Posibles causas:
  echo           - Falta de Internet
  echo           - Proxy corporativo
  echo           - Paquetes incompatibles
  echo.
  pause
  exit /b 1
)

REM 7) Ejecutar app
echo.
echo [INFO] Lanzando aplicacion...
echo.

"%VENV_PY%" -X faulthandler main.py ^
  1> launcher_stdout.log ^
  2> launcher_stderr.log
set "APP_EXIT=%ERRORLEVEL%"

echo.
if exist "launcher_stderr.log" (
  type "launcher_stderr.log"
)
echo.
if "%APP_EXIT%"=="0" (
  echo [INFO] La aplicacion se cerro correctamente.
) else (
  echo [WARN] La aplicacion termino con codigo: %APP_EXIT%
  echo        Si hubo un error, copia el mensaje de consola para depuracion.
)

echo.
pause
exit /b %APP_EXIT%
