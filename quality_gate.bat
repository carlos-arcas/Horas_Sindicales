@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "LOG_DIR=%ROOT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "LOG_STDOUT=%LOG_DIR%\quality_gate_stdout.log"
set "LOG_STDERR=%LOG_DIR%\quality_gate_stderr.log"
set "LOG_DEBUG=%LOG_DIR%\quality_gate_debug.log"

call :log_debug "==== quality_gate.bat ===="
call :log_debug "Repositorio: %ROOT_DIR%"

set "FAIL_STEP="
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
    call :log_debug "ERROR: No se encontro Python"
    goto INTERNAL_ERROR
)

if not exist ".venv\Scripts\python.exe" (
    call :log_debug "Creando .venv"
    %PYTHON_CMD% -m venv .venv >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
    if errorlevel 1 (
        call :log_debug "ERROR: Fallo creando .venv"
        goto INTERNAL_ERROR
    )
)

call ".venv\Scripts\activate.bat" >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    call :log_debug "ERROR: Fallo activando .venv"
    goto INTERNAL_ERROR
)

python --version >> "%LOG_DEBUG%" 2>&1

python -m pip install --upgrade pip >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    call :log_debug "ERROR: pip upgrade fallo"
    goto INTERNAL_ERROR
)

python -m pip install -r requirements-dev.txt >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    call :log_debug "ERROR: pip install requirements-dev.txt fallo"
    goto INTERNAL_ERROR
)

call :log_debug "Paso PRECHECK: preflight tests"
python scripts/preflight_tests.py >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 3 (
    set "FAIL_STEP=PRECHECK_INTERNO"
    call :log_debug "FAIL: PRECHECK_INTERNO"
    goto INTERNAL_ERROR
)
if errorlevel 2 (
    set "FAIL_STEP=PRECHECK_DEPS"
    call :log_debug "FAIL: PRECHECK_DEPS"
    goto GATE_FAIL
)
if errorlevel 1 (
    set "FAIL_STEP=PRECHECK"
    call :log_debug "FAIL: PRECHECK"
    goto GATE_FAIL
)

call :log_debug "Paso PRECHECK_UI: smoke handlers main window"
python scripts/ui_main_window_smoke.py >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    set "FAIL_STEP=PRECHECK_UI"
    call :log_debug "FAIL: PRECHECK_UI"
    goto GATE_FAIL
)

call :log_debug "Paso A: Auditoria E2E dry-run"
python -m app.entrypoints.cli_auditoria --dry-run >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    set "FAIL_STEP=AUDITOR"
    call :log_debug "FAIL: AUDITOR"
    goto GATE_FAIL
)

call :log_debug "Paso B: Pytest cobertura"
pytest --cov=app --cov-report=term-missing --cov-fail-under=85 >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    set "FAIL_STEP=PYTEST"
    call :log_debug "FAIL: PYTEST"
    goto GATE_FAIL
)

echo QUALITY GATE: PASS
goto END_OK

:GATE_FAIL
echo QUALITY GATE: FAIL
if defined FAIL_STEP echo Paso con fallo: %FAIL_STEP%
exit /b 2

:INTERNAL_ERROR
echo QUALITY GATE: FAIL
if not defined FAIL_STEP echo Paso con fallo: INTERNO
exit /b 3

:END_OK
exit /b 0

:log_debug
echo [%date% %time%] %~1>> "%LOG_DEBUG%"
exit /b 0
