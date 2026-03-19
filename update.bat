@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "LOG_DIR=%ROOT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "LOG_STDOUT=%LOG_DIR%\update_stdout.log"
set "LOG_STDERR=%LOG_DIR%\update_stderr.log"
set "LOG_DEBUG=%LOG_DIR%\update_debug.log"

call :log_debug "==== update.bat ===="
call :log_debug "Repositorio: %ROOT_DIR%"

call "%ROOT_DIR%setup.bat" >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    echo [ERROR] setup.bat fallo durante la actualizacion. Revisa logs.
    call :log_debug "ERROR: setup.bat fallo"
    exit /b 1
)

call ".venv\Scripts\activate.bat" >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    echo [ERROR] No se pudo activar .venv tras setup.
    call :log_debug "ERROR: Fallo activando .venv tras setup"
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
    echo [ERROR] Fallo al reinstalar requirements.txt. Revisa logs.
    call :log_debug "ERROR: reinstall requirements.txt fallo"
    exit /b 1
)

if exist "requirements-dev.txt" (
    python -m pip install -r requirements-dev.txt >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
    if errorlevel 1 (
        echo [ERROR] Fallo al reinstalar requirements-dev.txt. Revisa logs.
        call :log_debug "ERROR: reinstall requirements-dev.txt fallo"
        exit /b 1
    )
)

echo [OK] Entorno actualizado correctamente.
call :log_debug "Update completado"
exit /b 0

:log_debug
echo [%date% %time%] %~1>> "%LOG_DEBUG%"
exit /b 0
