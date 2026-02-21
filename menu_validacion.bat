@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "LOG_DIR=%ROOT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

set "SUMMARY_FILE=%LOG_DIR%\menu_ultima_ejecucion.txt"
set "TESTS_STDOUT=%LOG_DIR%\menu_tests_stdout.txt"
set "TESTS_STDERR=%LOG_DIR%\menu_tests_stderr.txt"
set "TESTS_ENV=%LOG_DIR%\menu_tests_env.txt"
set "TESTS_POST=%LOG_DIR%\menu_tests_postflight.txt"
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
    call :MENU_PREFLIGHT
    if errorlevel 1 goto MENU
    call :RUN_TESTS
    goto MENU
)

if "%CHOICE%"=="2" (
    call :MENU_PREFLIGHT
    if errorlevel 1 goto MENU
    call :RUN_GATE
    goto MENU
)

if "%CHOICE%"=="3" (
    call :MENU_PREFLIGHT
    if errorlevel 1 goto MENU
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

:MENU_PREFLIGHT
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

if not exist "%ROOT_DIR%ejecutar_tests.bat" (
    call :REPORT_PREFLIGHT_ERROR "ejecutar_tests.bat" "%ROOT_DIR%ejecutar_tests.bat"
    exit /b 1
)

if not exist "%ROOT_DIR%quality_gate.bat" (
    call :REPORT_PREFLIGHT_ERROR "quality_gate.bat" "%ROOT_DIR%quality_gate.bat"
    exit /b 1
)

exit /b 0

:REPORT_PREFLIGHT_ERROR
echo ERROR: No existe %~1 en %~2
>"%SUMMARY_FILE%" echo ERROR: No existe %~1 en %~2
>>"%SUMMARY_FILE%" echo Fecha: %DATE% %TIME%
>>"%SUMMARY_FILE%" echo ROOT_DIR: %ROOT_DIR%
exit /b 1

:RUN_TESTS
set "TESTS_EXEC=1"
set "GATE_EXEC=0"
set "LAST_ACTION=Ejecutar tests"
set "TESTS_COMMAND=call \"%ROOT_DIR%ejecutar_tests.bat\""

call :WRITE_TESTS_PREFLIGHT

call "%ROOT_DIR%ejecutar_tests.bat" 1>"%TESTS_STDOUT%" 2>"%TESTS_STDERR%"
set "TESTS_CODE=%ERRORLEVEL%"
call :WRITE_TESTS_POSTFLIGHT %TESTS_CODE%
if "%TESTS_CODE%"=="0" (
    set "TESTS_STATUS=PASS"
) else (
    set "TESTS_STATUS=FAIL"
)

set "GATE_CODE=NO_EJECUTADO"
set "GATE_STATUS=NO_EJECUTADO"

call :WRITE_SUMMARY
call :PRINT_RESULTS
exit /b %TESTS_CODE%

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
set "TESTS_COMMAND=call \"%ROOT_DIR%ejecutar_tests.bat\""

call :WRITE_TESTS_PREFLIGHT

call "%ROOT_DIR%ejecutar_tests.bat" 1>"%TESTS_STDOUT%" 2>"%TESTS_STDERR%"
set "TESTS_CODE=%ERRORLEVEL%"
call :WRITE_TESTS_POSTFLIGHT %TESTS_CODE%
if "%TESTS_CODE%"=="0" (
    set "TESTS_STATUS=PASS"
) else (
    set "TESTS_STATUS=FAIL"
)

if not "%TESTS_CODE%"=="0" (
    set "GATE_CODE=NO_EJECUTADO"
    set "GATE_STATUS=NO_EJECUTADO"
    call :WRITE_SUMMARY
    call :PRINT_RESULTS
    exit /b %TESTS_CODE%
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

:WRITE_TESTS_PREFLIGHT
>%TESTS_ENV% echo MENU VALIDACION - PRECHECK TESTS
>>%TESTS_ENV% echo Fecha: %DATE% %TIME%
>>%TESTS_ENV% echo CD=%CD%
>>%TESTS_ENV% echo ROOT_DIR=%ROOT_DIR%
>>%TESTS_ENV% echo PATH=%PATH%
>>%TESTS_ENV% echo.
>>%TESTS_ENV% echo ---- where python ----
where python >>%TESTS_ENV% 2>&1
>>%TESTS_ENV% echo ---- where pip ----
where pip >>%TESTS_ENV% 2>&1
>>%TESTS_ENV% echo ---- where pytest ----
where pytest >>%TESTS_ENV% 2>&1
>>%TESTS_ENV% echo.
>>%TESTS_ENV% echo ---- python --version ----
python --version >>%TESTS_ENV% 2>&1
>>%TESTS_ENV% echo ---- pip --version ----
pip --version >>%TESTS_ENV% 2>&1
>>%TESTS_ENV% echo ---- pytest --version ----
where pytest >nul 2>nul
if errorlevel 1 (
    >>%TESTS_ENV% echo [info] pytest no disponible en PATH
) else (
    pytest --version >>%TESTS_ENV% 2>&1
)
exit /b 0

:WRITE_TESTS_EMPTY_DIAG
>%TESTS_ENV% echo MENU VALIDACION - TESTS EMPTY STREAM DIAG
>>%TESTS_ENV% echo Fecha: %DATE% %TIME%
>>%TESTS_ENV% echo CD=%CD%
>>%TESTS_ENV% echo ROOT_DIR=%ROOT_DIR%
>>%TESTS_ENV% echo PATH=%PATH%
>>%TESTS_ENV% echo.
>>%TESTS_ENV% echo ---- where python ----
where python >>%TESTS_ENV% 2>&1
>>%TESTS_ENV% echo ---- where pip ----
where pip >>%TESTS_ENV% 2>&1
>>%TESTS_ENV% echo ---- where pytest ----
where pytest >>%TESTS_ENV% 2>&1
exit /b 0

:WRITE_TESTS_POSTFLIGHT
>%TESTS_POST% echo MENU VALIDACION - POSTCHECK TESTS
>>%TESTS_POST% echo Fecha: %DATE% %TIME%
>>%TESTS_POST% echo Comando: %TESTS_COMMAND%
>>%TESTS_POST% echo Exit code tests: %~1
if exist "%TESTS_STDOUT%" (
    for %%A in ("%TESTS_STDOUT%") do >>%TESTS_POST% echo Bytes stdout menu: %%~zA
) else (
    >>%TESTS_POST% echo Bytes stdout menu: [archivo inexistente]
)
if exist "%TESTS_STDERR%" (
    for %%A in ("%TESTS_STDERR%") do >>%TESTS_POST% echo Bytes stderr menu: %%~zA
) else (
    >>%TESTS_POST% echo Bytes stderr menu: [archivo inexistente]
)
exit /b 0

:WRITE_SUMMARY
>"%SUMMARY_FILE%" echo MENU VALIDACION - ULTIMA EJECUCION
>>"%SUMMARY_FILE%" echo Fecha: %DATE% %TIME%
>>"%SUMMARY_FILE%" echo Carpeta raiz: %ROOT_DIR%
>>"%SUMMARY_FILE%" echo Opcion: !LAST_ACTION!
if defined TESTS_COMMAND >>"%SUMMARY_FILE%" echo Comando tests: !TESTS_COMMAND!
>>"%SUMMARY_FILE%" echo.
>>"%SUMMARY_FILE%" echo TESTS: !TESTS_STATUS! ^(exit code !TESTS_CODE!^)
>>"%SUMMARY_FILE%" echo QUALITY GATE: !GATE_STATUS! ^(exit code !GATE_CODE!^)
>>"%SUMMARY_FILE%" echo.

if "!TESTS_EXEC!"=="1" (
    set "HAS_TESTS_STREAM=0"
    if exist "%TESTS_STDOUT%" for %%A in ("%TESTS_STDOUT%") do if %%~zA gtr 0 set "HAS_TESTS_STREAM=1"
    if exist "%TESTS_STDERR%" for %%A in ("%TESTS_STDERR%") do if %%~zA gtr 0 set "HAS_TESTS_STREAM=1"

    >>"%SUMMARY_FILE%" echo ===== TESTS PRE/POST FLIGHT =====
    >>"%SUMMARY_FILE%" echo --- logs\menu_tests_env.txt ---
    if exist "%TESTS_ENV%" (
        type "%TESTS_ENV%" >>"%SUMMARY_FILE%" 2>>"%SUMMARY_FILE%"
    ) else (
        >>"%SUMMARY_FILE%" echo [sin preflight de tests]
    )
    >>"%SUMMARY_FILE%" echo.
    if exist "%TESTS_POST%" (
        type "%TESTS_POST%" >>"%SUMMARY_FILE%" 2>>"%SUMMARY_FILE%"
    ) else (
        >>"%SUMMARY_FILE%" echo [sin postflight de tests]
    )
    >>"%SUMMARY_FILE%" echo.

    >>"%SUMMARY_FILE%" echo ===== TESTS STDOUT =====
    if exist "%TESTS_STDOUT%" (
        type "%TESTS_STDOUT%" >>"%SUMMARY_FILE%" 2>>"%SUMMARY_FILE%"
    ) else (
        >>"%SUMMARY_FILE%" echo [sin salida stdout de tests]
    )
    >>"%SUMMARY_FILE%" echo.
    >>"%SUMMARY_FILE%" echo ===== TESTS STDERR =====
    if exist "%TESTS_STDERR%" (
        type "%TESTS_STDERR%" >>"%SUMMARY_FILE%" 2>>"%SUMMARY_FILE%"
    ) else (
        >>"%SUMMARY_FILE%" echo [sin salida stderr de tests]
    )
    >>"%SUMMARY_FILE%" echo.

    if "!HAS_TESTS_STREAM!"=="0" (
        call :WRITE_TESTS_EMPTY_DIAG
        set "HAS_FALLBACK=0"
        >>"%SUMMARY_FILE%" echo ===== FALLBACK LOGS TESTS =====
        if exist "%LOG_DIR%\pytest_output.txt" (
            set "HAS_FALLBACK=1"
            >>"%SUMMARY_FILE%" echo --- logs\pytest_output.txt ---
            type "%LOG_DIR%\pytest_output.txt" >>"%SUMMARY_FILE%" 2>>"%SUMMARY_FILE%"
            >>"%SUMMARY_FILE%" echo.
        )
        if exist "%LOG_DIR%\coverage_report.txt" (
            set "HAS_FALLBACK=1"
            >>"%SUMMARY_FILE%" echo --- logs\coverage_report.txt ---
            type "%LOG_DIR%\coverage_report.txt" >>"%SUMMARY_FILE%" 2>>"%SUMMARY_FILE%"
            >>"%SUMMARY_FILE%" echo.
        )
        if "!HAS_FALLBACK!"=="0" (
            if exist "%TESTS_ENV%" (
                >>"%SUMMARY_FILE%" echo [fallback] stdout/stderr vacios; se adjunta menu_tests_env.txt
                type "%TESTS_ENV%" >>"%SUMMARY_FILE%" 2>>"%SUMMARY_FILE%"
            ) else (
                >>"%SUMMARY_FILE%" echo [fallback] stdout/stderr vacios y sin logs alternativos
            )
        )
        >>"%SUMMARY_FILE%" echo.
    )
)

if "!GATE_EXEC!"=="1" (
    >>"%SUMMARY_FILE%" echo ===== QUALITY GATE STDOUT =====
    if exist "%GATE_STDOUT%" (
        type "%GATE_STDOUT%" >>"%SUMMARY_FILE%" 2>>"%SUMMARY_FILE%"
    ) else (
        >>"%SUMMARY_FILE%" echo [sin salida stdout de quality gate]
    )
    >>"%SUMMARY_FILE%" echo.
    >>"%SUMMARY_FILE%" echo ===== QUALITY GATE STDERR =====
    if exist "%GATE_STDERR%" (
        type "%GATE_STDERR%" >>"%SUMMARY_FILE%" 2>>"%SUMMARY_FILE%"
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
