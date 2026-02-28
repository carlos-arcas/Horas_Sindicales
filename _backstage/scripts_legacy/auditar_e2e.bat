@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "LOG_DIR=%ROOT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

set "LOG_STDOUT=%LOG_DIR%\auditoria_e2e_stdout.log"
set "LOG_STDERR=%LOG_DIR%\auditoria_e2e_stderr.log"

set "MODE=%~1"
if "%MODE%"=="" set "MODE=--dry-run"

if /I not "%MODE%"=="--dry-run" if /I not "%MODE%"=="--write" (
    echo [ERROR] Uso: auditar_e2e.bat [--dry-run ^| --write]
    exit /b 1
)

set "PYTHON_CMD=.venv\Scripts\python.exe"
if not exist "%PYTHON_CMD%" (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
    ) else (
        set "PYTHON_CMD=python"
    )
)

echo Ejecutando auditoria E2E %MODE%
%PYTHON_CMD% -m app.entrypoints.cli_auditoria %MODE% >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
set "AUDIT_EXIT=%ERRORLEVEL%"

if "%AUDIT_EXIT%"=="0" (
    echo [PASS] Auditoria E2E %MODE%
) else (
    echo [FAIL] Auditoria E2E %MODE% ^(exit code: %AUDIT_EXIT%^)
)

echo Logs en: %LOG_STDOUT% y %LOG_STDERR%
exit /b %AUDIT_EXIT%
