@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
for %%I in ("%ROOT_DIR%..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "CHOICE="
set "LOG_DIR=%REPO_ROOT%\logs"
set "SUMMARY_FILE=%LOG_DIR%\menu_ultima_ejecucion.txt"
set "TESTS_STDOUT=%LOG_DIR%\menu_tests_stdout.txt"
set "TESTS_STDERR=%LOG_DIR%\menu_tests_stderr.txt"
set "GATE_STDOUT=%LOG_DIR%\menu_gate_stdout.txt"
set "GATE_STDERR=%LOG_DIR%\menu_gate_stderr.txt"
set "COVERAGE_REPORT=%LOG_DIR%\coverage_report.txt"
set "COVERAGE_HTML_DIR=%LOG_DIR%\htmlcov"
set "PYTHON_CMD="
set "TESTS_CODE=NO_EJECUTADO"
set "GATE_CODE=NO_EJECUTADO"
set "TESTS_STATUS=NO_EJECUTADO"
set "GATE_STATUS=NO_EJECUTADO"
set "LAST_ACTION=Sin ejecutar"
set "TESTS_EXEC=0"
set "GATE_EXEC=0"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

:MENU
echo.
echo ==============================================
echo Menu de validacion - Horas Sindicales
echo ==============================================
echo 1^) Ejecutar tests
echo 2^) Ejecutar quality gate
echo 3^) Ejecutar ambos ^(tests + quality gate^)
echo 4^) Abrir carpeta logs
echo 0^) Salir
set /p "CHOICE=> "

if "%CHOICE%"=="1" (
    set "LAST_ACTION=Ejecutar tests"
    call :MENU_PREFLIGHT || goto MENU
    call :RUN_TESTS
    goto MENU
)
if "%CHOICE%"=="2" (
    set "LAST_ACTION=Ejecutar quality gate"
    call :MENU_PREFLIGHT || goto MENU
    call :RUN_GATE
    goto MENU
)
if "%CHOICE%"=="3" (
    set "LAST_ACTION=Ejecutar ambos"
    call :MENU_PREFLIGHT || goto MENU
    call :RUN_TESTS
    if not "!TESTS_CODE!"=="0" (
        call :WRITE_SUMMARY
        call :PRINT_RESULTS
        goto MENU
    )
    call :RUN_GATE
    goto MENU
)
if "%CHOICE%"=="4" (
    if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
    start "" "%LOG_DIR%"
    goto MENU
)
if "%CHOICE%"=="0" goto END

echo Opcion invalida. Intenta de nuevo.
goto MENU

:MENU_PREFLIGHT
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
if not exist "%REPO_ROOT%\ejecutar_tests.bat" (
    call :REPORT_MISSING "ejecutar_tests.bat"
    exit /b 2
)
if not exist "%REPO_ROOT%\quality_gate.bat" (
    call :REPORT_MISSING "quality_gate.bat"
    exit /b 2
)
exit /b 0

:REPORT_MISSING
echo ERROR: No existe %~1 en "%REPO_ROOT%".
>"%SUMMARY_FILE%" echo MENU VALIDACION - ULTIMA EJECUCION
>>"%SUMMARY_FILE%" echo Fecha: %DATE% %TIME%
>>"%SUMMARY_FILE%" echo ROOT_DIR=%ROOT_DIR%
>>"%SUMMARY_FILE%" echo REPO_ROOT=%REPO_ROOT%
>>"%SUMMARY_FILE%" echo ERROR: archivo faltante %~1
exit /b 0

:RUN_TESTS
set "TESTS_EXEC=1"
set "GATE_EXEC=0"
set "TESTS_CODE=NO_EJECUTADO"
set "TESTS_STATUS=NO_EJECUTADO"

>"%TESTS_STDOUT%" echo REPO_ROOT=%REPO_ROOT%
>>"%TESTS_STDOUT%" echo ROOT_DIR=%ROOT_DIR%
>>"%TESTS_STDOUT%" echo DIR ejecutar_tests.bat
>>"%TESTS_STDOUT%" dir "%REPO_ROOT%\ejecutar_tests.bat" 2^>^&1

call "%REPO_ROOT%\ejecutar_tests.bat" 1>>"%TESTS_STDOUT%" 2>"%TESTS_STDERR%"
set "TESTS_CODE=%ERRORLEVEL%"
if "%TESTS_CODE%"=="0" (set "TESTS_STATUS=PASS") else (set "TESTS_STATUS=FAIL")

call :GENERATE_COVERAGE_ARTIFACTS
call :WRITE_SUMMARY
call :PRINT_RESULTS
exit /b %TESTS_CODE%

:RUN_GATE
set "GATE_EXEC=1"
set "GATE_CODE=NO_EJECUTADO"
set "GATE_STATUS=NO_EJECUTADO"

>"%GATE_STDOUT%" echo REPO_ROOT=%REPO_ROOT%
>>"%GATE_STDOUT%" echo ROOT_DIR=%ROOT_DIR%
>>"%GATE_STDOUT%" echo DIR quality_gate.bat
>>"%GATE_STDOUT%" dir "%REPO_ROOT%\quality_gate.bat" 2^>^&1

call "%REPO_ROOT%\quality_gate.bat" 1>>"%GATE_STDOUT%" 2>"%GATE_STDERR%"
set "GATE_CODE=%ERRORLEVEL%"
if "%GATE_CODE%"=="0" (set "GATE_STATUS=PASS") else (set "GATE_STATUS=FAIL")

call :WRITE_SUMMARY
call :PRINT_RESULTS
exit /b %GATE_CODE%

:GENERATE_COVERAGE_ARTIFACTS
if not exist "%REPO_ROOT%\.coverage" exit /b 0

if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%REPO_ROOT%\.venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

%PYTHON_CMD% -m coverage --version >nul 2>&1
if errorlevel 1 (
    %PYTHON_CMD% -m pip install coverage >>"%TESTS_STDOUT%" 2>>"%TESTS_STDERR%"
)

%PYTHON_CMD% -m coverage report -m >"%COVERAGE_REPORT%" 2>&1
if not exist "%COVERAGE_HTML_DIR%" mkdir "%COVERAGE_HTML_DIR%" >nul 2>&1
%PYTHON_CMD% -m coverage html -d "%COVERAGE_HTML_DIR%" >>"%COVERAGE_REPORT%" 2>&1
exit /b 0

:WRITE_SUMMARY
>"%SUMMARY_FILE%" echo MENU VALIDACION - ULTIMA EJECUCION
>>"%SUMMARY_FILE%" echo Fecha: %DATE% %TIME%
>>"%SUMMARY_FILE%" echo ROOT_DIR=%ROOT_DIR%
>>"%SUMMARY_FILE%" echo REPO_ROOT=%REPO_ROOT%
>>"%SUMMARY_FILE%" echo Opcion=%LAST_ACTION%
>>"%SUMMARY_FILE%" echo TESTS=%TESTS_STATUS% ^(exit %TESTS_CODE%^)
>>"%SUMMARY_FILE%" echo QUALITY_GATE=%GATE_STATUS% ^(exit %GATE_CODE%^)
if exist "%REPO_ROOT%\.coverage" (
    >>"%SUMMARY_FILE%" echo Coverage HTML: logs\htmlcov\index.html
)

if "%TESTS_EXEC%"=="1" (
    >>"%SUMMARY_FILE%" echo.
    >>"%SUMMARY_FILE%" echo --- STDERR tests (primeras 200 lineas si falla) ---
    if not "%TESTS_CODE%"=="0" (
        if exist "%TESTS_STDERR%" (
            for /f "usebackq tokens=1,* delims=:" %%A in (`findstr /n "^" "%TESTS_STDERR%"`) do (
                if %%A LEQ 200 >>"%SUMMARY_FILE%" echo %%B
            )
        )
    )
    findstr /c:"El sistema no puede encontrar la ruta especificada." "%TESTS_STDERR%" >nul 2>&1
    if not errorlevel 1 call :WRITE_PATH_DIAGNOSTIC
)

if "%GATE_EXEC%"=="1" (
    >>"%SUMMARY_FILE%" echo.
    >>"%SUMMARY_FILE%" echo --- STDERR quality gate (primeras 200 lineas si falla) ---
    if not "%GATE_CODE%"=="0" (
        if exist "%GATE_STDERR%" (
            for /f "usebackq tokens=1,* delims=:" %%A in (`findstr /n "^" "%GATE_STDERR%"`) do (
                if %%A LEQ 200 >>"%SUMMARY_FILE%" echo %%B
            )
        )
    )
    findstr /c:"El sistema no puede encontrar la ruta especificada." "%GATE_STDERR%" >nul 2>&1
    if not errorlevel 1 call :WRITE_PATH_DIAGNOSTIC
)
exit /b 0

:WRITE_PATH_DIAGNOSTIC
>>"%SUMMARY_FILE%" echo.
>>"%SUMMARY_FILE%" echo --- DIAGNOSTICO DE RUTAS ---
>>"%SUMMARY_FILE%" echo REPO_ROOT=%REPO_ROOT%
>>"%SUMMARY_FILE%" echo ROOT_DIR=%ROOT_DIR%
>>"%SUMMARY_FILE%" echo [where python]
where python >>"%SUMMARY_FILE%" 2>&1
>>"%SUMMARY_FILE%" echo [where pip]
where pip >>"%SUMMARY_FILE%" 2>&1
>>"%SUMMARY_FILE%" echo [dir .venv\Scripts]
dir "%REPO_ROOT%\.venv\Scripts" >>"%SUMMARY_FILE%" 2>&1
exit /b 0

:PRINT_RESULTS
echo.
echo TESTS: %TESTS_STATUS% ^(exit %TESTS_CODE%^)
echo QUALITY GATE: %GATE_STATUS% ^(exit %GATE_CODE%^)
echo Resumen: logs\menu_ultima_ejecucion.txt
exit /b 0

:END
echo Saliendo del menu de validacion.
exit /b 0
