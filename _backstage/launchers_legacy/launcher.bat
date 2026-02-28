@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "LOG_DIR=%ROOT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

echo ==============================================
echo Horas Sindicales - Launcher operativo

echo Scripts: %ROOT_DIR%
echo Logs:    %LOG_DIR%
echo ==============================================

:MENU
echo.
echo Selecciona una opcion:
echo 1) Lanzar app

echo 2) Ejecutar tests

echo 3) Quality gate

echo 4) Auditor E2E ^(dry-run^)

echo 5) Auditor E2E ^(write^)

echo 0) Salir
set /p "CHOICE=> "

if "%CHOICE%"=="1" (
    call :RUN "Lanzar app" "%ROOT_DIR%lanzar_app.bat"
    goto MENU
)

if "%CHOICE%"=="2" (
    call :RUN "Ejecutar tests" "%ROOT_DIR%ejecutar_tests.bat"
    goto MENU
)

if "%CHOICE%"=="3" (
    call :RUN "Quality gate" "%ROOT_DIR%quality_gate.bat"
    goto MENU
)

if "%CHOICE%"=="4" (
    call :RUN "Auditor E2E dry-run" "%ROOT_DIR%auditar_e2e.bat" --dry-run
    goto MENU
)

if "%CHOICE%"=="5" (
    call :RUN "Auditor E2E write" "%ROOT_DIR%auditar_e2e.bat" --write
    goto MENU
)

if "%CHOICE%"=="0" goto END

echo Opcion invalida. Intenta de nuevo.
goto MENU

:RUN
set "LABEL=%~1"
set "SCRIPT=%~2"
shift
shift

if not exist "%SCRIPT%" (
    echo [FAIL] %LABEL% - no existe script: %SCRIPT%
    exit /b 1
)

echo.
echo Ejecutando: %LABEL%
call "%SCRIPT%" %*
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo [PASS] %LABEL%
) else (
    echo [FAIL] %LABEL% ^(exit code: %EXIT_CODE%^)
)

echo Logs disponibles en: %LOG_DIR%
exit /b %EXIT_CODE%

:END
echo Saliendo del launcher.
exit /b 0
