@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "LOG_DIR=%ROOT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

set "SUMMARY_FILE=%LOG_DIR%\menu_ultima_ejecucion.txt"
set "TESTS_STDOUT=%LOG_DIR%\menu_tests_stdout.txt"
set "TESTS_STDERR=%LOG_DIR%\menu_tests_stderr.txt"
set "GATE_STDOUT=%LOG_DIR%\menu_gate_stdout.txt"
set "GATE_STDERR=%LOG_DIR%\menu_gate_stderr.txt"

:MENU
echo.
echo ==============================================
echo Menu de validacion - Horas Sindicales
echo ==============================================
echo 1) Ejecutar tests
echo 2) Ejecutar quality gate
echo 3) Ejecutar ambos ^(tests + quality gate^)
echo 4) Abrir carpeta logs
echo 0) Salir
set /p "CHOICE=> "

if "%CHOICE%"=="1" (
    call :RUN_TESTS
    goto MENU
)

if "%CHOICE%"=="2" (
    call :RUN_GATE
    goto MENU
)

if "%CHOICE%"=="3" (
    call :RUN_BOTH
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

:RUN_TESTS
set "TESTS_EXEC=1"
set "GATE_EXEC=0"
set "LAST_ACTION=Ejecutar tests"

call "%ROOT_DIR%ejecutar_tests.bat" 1>"%TESTS_STDOUT%" 2>"%TESTS_STDERR%"
set "TESTS_CODE=!ERRORLEVEL!"
if "!TESTS_CODE!"=="0" (
    set "TESTS_STATUS=PASS"
) else (
    set "TESTS_STATUS=FAIL"
)

set "GATE_CODE=NO_EJECUTADO"
set "GATE_STATUS=NO_EJECUTADO"

call :WRITE_SUMMARY
call :PRINT_RESULTS
exit /b !TESTS_CODE!

:RUN_GATE
set "TESTS_EXEC=0"
set "GATE_EXEC=1"
set "LAST_ACTION=Ejecutar quality gate"

call "%ROOT_DIR%quality_gate.bat" 1>"%GATE_STDOUT%" 2>"%GATE_STDERR%"
set "GATE_CODE=!ERRORLEVEL!"
if "!GATE_CODE!"=="0" (
    set "GATE_STATUS=PASS"
) else (
    set "GATE_STATUS=FAIL"
)

set "TESTS_CODE=NO_EJECUTADO"
set "TESTS_STATUS=NO_EJECUTADO"

call :WRITE_SUMMARY
call :PRINT_RESULTS
if "!GATE_CODE!"=="NO_EJECUTADO" exit /b 1
exit /b !GATE_CODE!

:RUN_BOTH
set "TESTS_EXEC=1"
set "GATE_EXEC=0"
set "LAST_ACTION=Ejecutar ambos en orden"

call "%ROOT_DIR%ejecutar_tests.bat" 1>"%TESTS_STDOUT%" 2>"%TESTS_STDERR%"
set "TESTS_CODE=!ERRORLEVEL!"
if "!TESTS_CODE!"=="0" (
    set "TESTS_STATUS=PASS"
) else (
    set "TESTS_STATUS=FAIL"
)

if not "!TESTS_CODE!"=="0" (
    set "GATE_CODE=NO_EJECUTADO"
    set "GATE_STATUS=NO_EJECUTADO"
    call :WRITE_SUMMARY
    call :PRINT_RESULTS
    exit /b !TESTS_CODE!
)

set "GATE_EXEC=1"
call "%ROOT_DIR%quality_gate.bat" 1>"%GATE_STDOUT%" 2>"%GATE_STDERR%"
set "GATE_CODE=!ERRORLEVEL!"
if "!GATE_CODE!"=="0" (
    set "GATE_STATUS=PASS"
) else (
    set "GATE_STATUS=FAIL"
)

call :WRITE_SUMMARY
call :PRINT_RESULTS
exit /b !GATE_CODE!

:WRITE_SUMMARY
>"%SUMMARY_FILE%" echo MENU VALIDACION - ULTIMA EJECUCION
>>"%SUMMARY_FILE%" echo Fecha: %DATE% %TIME%
>>"%SUMMARY_FILE%" echo Carpeta raiz: %ROOT_DIR%
>>"%SUMMARY_FILE%" echo Opcion: !LAST_ACTION!
>>"%SUMMARY_FILE%" echo.
>>"%SUMMARY_FILE%" echo TESTS: !TESTS_STATUS! ^(exit code !TESTS_CODE!^)
>>"%SUMMARY_FILE%" echo QUALITY GATE: !GATE_STATUS! ^(exit code !GATE_CODE!^)
>>"%SUMMARY_FILE%" echo.

if "!TESTS_EXEC!"=="1" (
    >>"%SUMMARY_FILE%" echo ===== TESTS STDOUT =====
    if exist "%TESTS_STDOUT%" (
        type "%TESTS_STDOUT%" >>"%SUMMARY_FILE%"
    ) else (
        >>"%SUMMARY_FILE%" echo [sin salida stdout de tests]
    )
    >>"%SUMMARY_FILE%" echo.
    >>"%SUMMARY_FILE%" echo ===== TESTS STDERR =====
    if exist "%TESTS_STDERR%" (
        type "%TESTS_STDERR%" >>"%SUMMARY_FILE%"
    ) else (
        >>"%SUMMARY_FILE%" echo [sin salida stderr de tests]
    )
    >>"%SUMMARY_FILE%" echo.
)

if "!GATE_EXEC!"=="1" (
    >>"%SUMMARY_FILE%" echo ===== QUALITY GATE STDOUT =====
    if exist "%GATE_STDOUT%" (
        type "%GATE_STDOUT%" >>"%SUMMARY_FILE%"
    ) else (
        >>"%SUMMARY_FILE%" echo [sin salida stdout de quality gate]
    )
    >>"%SUMMARY_FILE%" echo.
    >>"%SUMMARY_FILE%" echo ===== QUALITY GATE STDERR =====
    if exist "%GATE_STDERR%" (
        type "%GATE_STDERR%" >>"%SUMMARY_FILE%"
    ) else (
        >>"%SUMMARY_FILE%" echo [sin salida stderr de quality gate]
    )
    >>"%SUMMARY_FILE%" echo.
)
exit /b 0

:PRINT_RESULTS
echo.
echo TESTS: !TESTS_STATUS! ^(exit code !TESTS_CODE!^)
echo QUALITY GATE: !GATE_STATUS! ^(exit code !GATE_CODE!^)
echo Salida guardada en logs\menu_ultima_ejecucion.txt
exit /b 0

:END
echo Saliendo del menu de validacion.
exit /b 0
