@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "LOG_DIR=%ROOT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "LOG_STDOUT=%LOG_DIR%\setup_stdout.log"
set "LOG_STDERR=%LOG_DIR%\setup_stderr.log"
set "LOG_DEBUG=%LOG_DIR%\setup_debug.log"

call :log_debug "==== setup.bat ===="
call :log_debug "Repositorio: %ROOT_DIR%"

set "PYTHON_CMD="
set "PYTHON_EXE=.venv\Scripts\python.exe"

if exist "%PYTHON_EXE%" (
    set "PYTHON_CMD=%PYTHON_EXE%"
    call :log_debug "Python detectado en .venv"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
        call :log_debug "Python detectado via py -3"
    ) else (
        where python >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_CMD=python"
            call :log_debug "Python detectado via python"
        )
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] No se encontro Python (^".venv\Scripts\python.exe^", ^"py -3^" ni ^"python^"^).
    call :log_debug "ERROR: No se encontro Python"
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    call :log_debug "Creando .venv"
    %PYTHON_CMD% -m venv .venv >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
    if errorlevel 1 (
        echo [ERROR] Fallo al crear .venv. Revisa logs.
        call :log_debug "ERROR: Fallo creando .venv"
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat" >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    echo [ERROR] No se pudo activar .venv.
    call :log_debug "ERROR: Fallo activando .venv"
    exit /b 1
)

python -m pip install --upgrade pip >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    echo [ERROR] Fallo al actualizar pip. Revisa logs.
    call :log_debug "ERROR: pip upgrade fallo"
    exit /b 1
)

python -m pip install -r requirements.txt >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    echo [ERROR] Fallo al instalar requirements.txt. Revisa logs.
    call :log_debug "ERROR: pip install requirements.txt fallo"
    exit /b 1
)

if exist "requirements-dev.txt" (
    python -m pip install -r requirements-dev.txt >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
    if errorlevel 1 (
        echo [ERROR] Fallo al instalar requirements-dev.txt. Revisa logs.
        call :log_debug "ERROR: pip install requirements-dev.txt fallo"
        exit /b 1
    )
)

echo [OK] Entorno preparado correctamente.
call :log_debug "Setup completado"
exit /b 0

:log_debug
echo [%date% %time%] %~1>> "%LOG_DEBUG%"
exit /b 0
