@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================================
REM  launch.bat - Launcher Windows (doble click)
REM ==========================================================

cd /d "%~dp0"

set "PROJECT_DIR=%CD%"
set "LOG_DIR=%PROJECT_DIR%\logs"
set "FALLBACK_LOG_DIR=%TEMP%\HorasSindicales\logs"

if not exist "%LOG_DIR%" (
  mkdir "%LOG_DIR%" 2>nul
)
if not exist "%LOG_DIR%" (
  set "LOG_DIR=%FALLBACK_LOG_DIR%"
  if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" 2>nul
)
if not exist "%LOG_DIR%" (
  set "LOG_DIR=%PROJECT_DIR%"
)

set "LOG_DEBUG=%LOG_DIR%\launcher_debug.log"
set "LOG_STDOUT=%LOG_DIR%\launcher_stdout.log"
set "LOG_STDERR=%LOG_DIR%\launcher_stderr.log"
set "TRACE=%PROJECT_DIR%\TRACE_LAUNCHER.txt"

> "%TRACE%" echo [%DATE% %TIME%] Inicio launcher en %CD%

echo ============================================
echo Launcher Horas Sindicales iniciado
echo Carpeta: %CD%
echo TRACE: %TRACE%
echo ============================================
echo.

if not exist "main.py" (
  echo [ERROR] No se encuentra main.py
  >> "%TRACE%" echo ERROR: no main.py
  goto :end
)

if not exist "requirements.txt" (
  echo [ERROR] No se encuentra requirements.txt
  >> "%TRACE%" echo ERROR: no requirements.txt
  goto :end
)

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python no esta en PATH
  >> "%TRACE%" echo ERROR: python no en PATH
  goto :end
)

if not exist ".venv" (
  echo [INFO] Creando entorno virtual .venv...
  >> "%TRACE%" echo Creando venv
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Fallo creando .venv
    >> "%TRACE%" echo ERROR: fallo venv
    goto :end
  )
)

set "VENV_PY=%CD%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo [ERROR] No existe %VENV_PY%
  >> "%TRACE%" echo ERROR: no VENV_PY
  goto :end
)

echo [INFO] Actualizando pip...
"%VENV_PY%" -m pip install --upgrade pip >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
  echo [ERROR] pip upgrade fallo
  goto :end
)

echo [INFO] Instalando dependencias...
"%VENV_PY%" -m pip install -r requirements.txt >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
  echo [ERROR] pip install fallo
  goto :end
)

echo [INFO] Ejecutando aplicacion...
"%VENV_PY%" main.py
set "APP_EXIT=%ERRORLEVEL%"
>> "%TRACE%" echo main.py exit=%APP_EXIT%

:end
echo.
echo ============================================
echo Fin del launcher
echo Logs en:
echo   %LOG_DIR%
echo ============================================
echo.
pause
endlocal
exit /b 0
