@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "LOG_DIR=%ROOT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

call :LOG_EVENT "launcher_start" "launcher.bat" "begin" "%~1"

if "%~1"=="" (
    call :LOG_EVENT "launcher_mode" "launcher.bat" "default_app" "-"
    call :RUN "Lanzar app" "%ROOT_DIR%lanzar_app.bat"
    exit /b %ERRORLEVEL%
)

if /I "%~1"=="menu" goto MENU
if /I "%~1"=="app" (
    call :RUN_APP_COMMAND %*
    exit /b %ERRORLEVEL%
)
if /I "%~1"=="tests" (
    call :RUN "Ejecutar tests" "%ROOT_DIR%ejecutar_tests.bat"
    exit /b %ERRORLEVEL%
)
if /I "%~1"=="quality" (
    call :RUN "Quality gate" "%ROOT_DIR%quality_gate.bat"
    exit /b %ERRORLEVEL%
)
if /I "%~1"=="audit-dry-run" (
    call :RUN "Auditor E2E dry-run" "%ROOT_DIR%auditar_e2e.bat" --dry-run
    exit /b %ERRORLEVEL%
)
if /I "%~1"=="audit-write" (
    call :RUN "Auditor E2E write" "%ROOT_DIR%auditar_e2e.bat" --write
    exit /b %ERRORLEVEL%
)
if /I "%~1"=="help" goto HELP

call :LOG_EVENT "launcher_mode" "launcher.bat" "forward_app_args" "%~1"
call :RUN "Lanzar app" "%ROOT_DIR%lanzar_app.bat" %*
exit /b %ERRORLEVEL%

:MENU
echo ==============================================
echo Horas Sindicales - Launcher operativo
echo Scripts: %ROOT_DIR%
echo Logs:    %LOG_DIR%
echo ==============================================
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

:RUN_APP_COMMAND
shift
call :LOG_EVENT "launcher_mode" "launcher.bat" "explicit_app" "%~1"
call :RUN "Lanzar app" "%ROOT_DIR%lanzar_app.bat" %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%

:RUN
set "LABEL=%~1"
set "SCRIPT=%~2"
shift
shift

if not exist "%SCRIPT%" (
    echo [FAIL] %LABEL% - no existe script: %SCRIPT%
    call :LOG_EVENT "launcher_run" "launcher.bat" "missing_script" "%LABEL%"
    exit /b 1
)

echo.
echo Ejecutando: %LABEL%
call :LOG_EVENT "launcher_run" "launcher.bat" "start" "%LABEL%"
call "%SCRIPT%" %1 %2 %3 %4 %5 %6 %7 %8 %9
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo [PASS] %LABEL%
    call :LOG_EVENT "launcher_run" "launcher.bat" "pass" "%LABEL%"
) else (
    echo [FAIL] %LABEL% ^(exit code: %EXIT_CODE%^)
    call :LOG_EVENT "launcher_run" "launcher.bat" "fail" "%LABEL%"
)

echo Logs disponibles en: %LOG_DIR%
exit /b %EXIT_CODE%

:HELP
echo Uso:
echo   launcher.bat               ^> lanza la app
echo   launcher.bat menu          ^> abre el menu interactivo
echo   launcher.bat app [args]    ^> lanza la app con argumentos extra
echo   launcher.bat --selfcheck   ^> reenvia el selfcheck al entrypoint Python
echo   launcher.bat tests         ^> ejecuta tests
echo   launcher.bat quality       ^> ejecuta quality gate
echo   launcher.bat audit-dry-run ^> ejecuta auditoria E2E en modo dry-run
echo   launcher.bat audit-write   ^> ejecuta auditoria E2E en modo write
exit /b 0

:LOG_EVENT
>> "%LOG_DIR%\launcher_debug.log" echo [%date% %time%] action=%~1 module=%~2 result=%~3 detail=%~4
exit /b 0

:END
echo Saliendo del launcher.
exit /b 0
