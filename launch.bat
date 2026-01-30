@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================================
REM  launch.bat - Launcher Windows para app PySide6 (Horas Sindicales)
REM  Modo blindado con logs persistentes.
REM ==========================================================

REM 0) Forzar consola persistente
if /I not "%~1"=="__in_cmd__" (
  start "" cmd /k ""%~f0" __in_cmd__"
  exit /b 0
)

REM 1) Ir al directorio del launcher (raíz del proyecto)
cd /d "%~dp0"

REM 2) Preparar directorio de logs
set "PROJECT_DIR=%CD%"
set "LOG_DIR=%PROJECT_DIR%\logs"
set "FALLBACK_LOG_DIR=%TEMP%\HorasSindicales\logs"

if not exist "%LOG_DIR%" (
  mkdir "%LOG_DIR%" 2>nul
)
if not exist "%LOG_DIR%" (
  set "LOG_DIR=%FALLBACK_LOG_DIR%"
  if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%" 2>nul
  )
)

if not exist "%LOG_DIR%" (
  echo [ERROR] No se pudo crear directorio de logs en "%PROJECT_DIR%" ni en "%FALLBACK_LOG_DIR%".
  echo [ERROR] Se usara el directorio actual como ultimo recurso.
  set "LOG_DIR=%PROJECT_DIR%"
)

set "HORAS_LOG_DIR=%LOG_DIR%"
set "LOG_DEBUG=%LOG_DIR%\launcher_debug.log"
set "LOG_STDOUT=%LOG_DIR%\launcher_stdout.log"
set "LOG_STDERR=%LOG_DIR%\launcher_stderr.log"

call :log "============================================"
call :log "Launcher Horas Sindicales iniciado"
call :log "PROJECT_DIR=%PROJECT_DIR%"
call :log "LOG_DIR=%LOG_DIR%"
call :log "CMDLINE=%~f0 %*"

REM 3) Sentinel de ejecucion
set "SENTINEL=%LOG_DIR%\launcher_ran.txt"
> "%SENTINEL%" (
  echo [%DATE% %TIME%] Launcher ejecutado.
  echo CD=%CD%
)

REM 4) Comprobaciones basicas
if not exist "main.py" (
  call :log "[ERROR] No se encuentra main.py en %CD%"
  echo [ERROR] No se encuentra main.py en la carpeta actual: %CD%
  echo Logs: %LOG_DIR%
  pause
  goto :end
)

if not exist "requirements.txt" (
  call :log "[ERROR] No se encuentra requirements.txt en %CD%"
  echo [ERROR] No se encuentra requirements.txt en la carpeta actual: %CD%
  echo Logs: %LOG_DIR%
  pause
  goto :end
)

REM 5) Detectar Python del venv
set "VENV_PY=%CD%\.venv\Scripts\python.exe"
set "VENV_PIP=%CD%\.venv\Scripts\pip.exe"

if exist "%VENV_PY%" (
  call :log "[INFO] Python del venv encontrado: %VENV_PY%"
) else (
  call :log "[INFO] No existe .venv. Se intentara crear."
  where python >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
  if errorlevel 1 (
    call :log "[ERROR] No se encuentra 'python' en PATH."
    echo [ERROR] No se encuentra "python" en PATH.
    echo Logs: %LOG_DIR%
    pause
    goto :end
  )
  python -m venv .venv >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
  if errorlevel 1 (
    call :log "[ERROR] Fallo creando el entorno virtual (.venv)."
    echo [ERROR] Fallo creando el entorno virtual (.venv).
    echo Logs: %LOG_DIR%
    pause
    goto :end
  )
)

if not exist "%VENV_PY%" (
  call :log "[ERROR] No se encuentra el Python del entorno virtual: %VENV_PY%"
  echo [ERROR] No se encuentra el Python del entorno virtual: %VENV_PY%
  echo Logs: %LOG_DIR%
  pause
  goto :end
)

REM 6) Variables de entorno para Python
set "PYTHONFAULTHANDLER=1"
set "PYTHONUTF8=1"

REM 7) Actualizar pip e instalar dependencias
call :log "[INFO] Actualizando pip..."
"%VENV_PY%" -m pip install --upgrade pip >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
  call :log "[ERROR] No se pudo actualizar pip."
  echo [ERROR] No se pudo actualizar pip.
  echo Logs: %LOG_DIR%
  pause
  goto :end
)

call :log "[INFO] Instalando/verificando dependencias..."
"%VENV_PY%" -m pip install -r requirements.txt >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
  call :log "[ERROR] Fallo instalando dependencias."
  echo [ERROR] Fallo instalando dependencias.
  echo Logs: %LOG_DIR%
  pause
  goto :end
)

REM 8) Selfcheck previo
call :log "[INFO] Ejecutando selfcheck..."
"%VENV_PY%" -X faulthandler -u main.py --selfcheck >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
set "SELF_RC=%ERRORLEVEL%"
if not "%SELF_RC%"=="0" (
  call :log "[ERROR] Selfcheck fallo con codigo %SELF_RC%."
  echo [ERROR] Selfcheck fallo. Revisa logs.
  echo Logs: %LOG_DIR%
  pause
  goto :end
)

REM 9) Ejecutar app
call :log "[INFO] Lanzando aplicacion..."
"%VENV_PY%" -X faulthandler -u main.py >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
set "APP_EXIT=%ERRORLEVEL%"
call :log "[INFO] Aplicacion finalizo con codigo %APP_EXIT%"

echo.
echo ============================================
echo Logs guardados en:
echo   %LOG_DIR%
echo Sentinel:
echo   %SENTINEL%
echo ============================================
echo.

pause

goto :end

:log
set "MSG=%*"
echo %MSG%
>> "%LOG_DEBUG%" echo [%DATE% %TIME%] %MSG%
exit /b 0

:end
endlocal
