@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "REPO_ROOT=%ROOT_DIR%"
set "LOG_DIR=%REPO_ROOT%\logs"
set "RUNS_DIR=%LOG_DIR%\runs"
set "SUMMARY_FILE=%LOG_DIR%\menu_ultima_ejecucion.txt"
set "TESTS_ENV_FILE=%LOG_DIR%\menu_tests_env.txt"
set "LAST_RUN_ID_FILE=%LOG_DIR%\menu_last_run_id.txt"
set "TESTS_SCRIPT=%REPO_ROOT%\ejecutar_tests.bat"
set "GATE_SCRIPT=%REPO_ROOT%\quality_gate.bat"

set "SCRIPT_EXIT_CODE=0"
set "CHOICE="
set "LAST_ACTION=Sin ejecutar"
set "TESTS_STATUS=NO_EJECUTADO"
set "TESTS_CODE=NO_EJECUTADO"
set "GATE_STATUS=NO_EJECUTADO"
set "GATE_CODE=NO_EJECUTADO"
set "RUN_DIR="
set "RUN_ID="
set "RUN_STEP_FAILED=0"
set "LAST_ERROR_STEP="
set "LAST_ERROR_REASON="
set "LAST_ERROR_STDOUT="
set "LAST_ERROR_STDERR="
set "LAST_ERROR_CMD="
set "LAST_ERROR_EXIT="
set "PAUSE_ALREADY_DONE=0"
set "DEBUG_SANITY=0"

call :ENSURE_LOG_DIRS
cd /d "%REPO_ROOT%"

:MENU
echo.
echo ==============================================
echo Menu de validacion - Horas Sindicales
echo ==============================================
echo 1^) Ejecutar tests
echo 2^) Ejecutar quality gate
echo 3^) Ejecutar ambos ^(tests + quality gate^)
echo 4^) Abrir carpeta logs
echo 5^) Abrir el ultimo summary en Notepad
echo 6^) Abrir coverage html ^(index.html^) del ultimo run
echo 9^) [debug] Self-test run_step con dummy_fail
echo 0^) Salir
set /p "CHOICE=> "

if "%CHOICE%"=="1" (
    set "LAST_ACTION=Ejecutar tests"
    set "PAUSE_ALREADY_DONE=0"
    call :RUN_PREFLIGHT || (
        call :FINALIZE_ACTION
        goto MENU
    )
    call :RUN_TESTS
    call :WRITE_SUMMARY
    call :PUBLISH_LAST_SUMMARY
    set "SCRIPT_EXIT_CODE=!TESTS_CODE!"
    call :WRITE_MENU_EXECUTION_LOG "%LAST_ACTION%" "!SCRIPT_EXIT_CODE!"
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="2" (
    set "LAST_ACTION=Ejecutar quality gate"
    set "PAUSE_ALREADY_DONE=0"
    call :RUN_PREFLIGHT || (
        call :FINALIZE_ACTION
        goto MENU
    )
    call :RUN_GATE
    echo QUALITY GATE: !GATE_STATUS! exit code !GATE_CODE!
    call :WRITE_SUMMARY
    call :PUBLISH_LAST_SUMMARY
    set "SCRIPT_EXIT_CODE=!GATE_CODE!"
    call :WRITE_MENU_EXECUTION_LOG "%LAST_ACTION%" "!SCRIPT_EXIT_CODE!"
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="3" (
    set "LAST_ACTION=Ejecutar ambos"
    set "PAUSE_ALREADY_DONE=0"
    call :RUN_PREFLIGHT || (
        call :FINALIZE_ACTION
        goto MENU
    )
    call :RUN_TESTS
    if not "!TESTS_CODE!"=="0" (
        set "GATE_STATUS=NO_EJECUTADO"
        set "GATE_CODE=NO_EJECUTADO"
        call :WRITE_SUMMARY
        call :PUBLISH_LAST_SUMMARY
        set "SCRIPT_EXIT_CODE=!TESTS_CODE!"
        call :WRITE_MENU_EXECUTION_LOG "%LAST_ACTION%" "!SCRIPT_EXIT_CODE!"
        call :FINALIZE_ACTION
        goto MENU
    )
    call :RUN_GATE
    call :WRITE_SUMMARY
    call :PUBLISH_LAST_SUMMARY
    set "SCRIPT_EXIT_CODE=!GATE_CODE!"
    call :WRITE_MENU_EXECUTION_LOG "%LAST_ACTION%" "!SCRIPT_EXIT_CODE!"
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="4" (
    set "PAUSE_ALREADY_DONE=0"
    if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
    start "" "%LOG_DIR%"
    call :WRITE_MENU_EXECUTION_LOG "Abrir carpeta logs" "0"
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="5" (
    set "PAUSE_ALREADY_DONE=0"
    if exist "%SUMMARY_FILE%" (
        start "" notepad "%SUMMARY_FILE%"
    ) else (
        echo No existe aun "%SUMMARY_FILE%".
    )
    call :WRITE_MENU_EXECUTION_LOG "Abrir el ultimo summary en Notepad" "0"
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="6" (
    set "PAUSE_ALREADY_DONE=0"
    call :OPEN_LAST_COVERAGE_HTML
    call :WRITE_MENU_EXECUTION_LOG "Abrir coverage html (index.html) del ultimo run" "%ERRORLEVEL%"
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="9" (
    set "LAST_ACTION=Debug self-test run_step"
    set "PAUSE_ALREADY_DONE=0"
    set "DEBUG_SANITY=1"
    call :RUN_PREFLIGHT || (
        set "DEBUG_SANITY=0"
        call :FINALIZE_ACTION
        goto MENU
    )
    call :RUN_DEBUG_SELF_TEST
    set "DEBUG_SANITY=0"
    call :WRITE_SUMMARY
    call :PUBLISH_LAST_SUMMARY
    set "SCRIPT_EXIT_CODE=!TESTS_CODE!"
    call :WRITE_MENU_EXECUTION_LOG "%LAST_ACTION%" "!SCRIPT_EXIT_CODE!"
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="0" goto END

echo Opcion invalida. Intenta de nuevo.
call :WRITE_MENU_EXECUTION_LOG "Opcion invalida" "1"
call :FINALIZE_ACTION
goto MENU

:RUN_PREFLIGHT
call :ENSURE_LOG_DIRS
if not exist "%TESTS_SCRIPT%" (
    call :SET_ERROR_STATE "preflight" "" "%SUMMARY_FILE%" "%SUMMARY_FILE%" "2" "No existe ejecutar_tests.bat"
    call :HANDLE_STEP_ERROR
    exit /b 1
)
if not exist "%GATE_SCRIPT%" (
    call :SET_ERROR_STATE "preflight" "" "%SUMMARY_FILE%" "%SUMMARY_FILE%" "2" "No existe quality_gate.bat"
    call :HANDLE_STEP_ERROR
    exit /b 1
)
call :CREATE_RUN_DIR || exit /b 1
set "TESTS_STATUS=NO_EJECUTADO"
set "TESTS_CODE=NO_EJECUTADO"
set "GATE_STATUS=NO_EJECUTADO"
set "GATE_CODE=NO_EJECUTADO"
set "RUN_STEP_FAILED=0"
set "LAST_ERROR_STEP="
set "LAST_ERROR_REASON="
set "LAST_ERROR_STDOUT="
set "LAST_ERROR_STDERR="
set "LAST_ERROR_CMD="
set "LAST_ERROR_EXIT="
exit /b 0

:CREATE_RUN_DIR
set "RUN_ID=%DATE%_%TIME%"
set "RUN_ID=%RUN_ID:/=%"
set "RUN_ID=%RUN_ID::=%"
set "RUN_ID=%RUN_ID:.=%"
set "RUN_ID=%RUN_ID:,=%"
set "RUN_ID=%RUN_ID: =0%"
set "RUN_DIR=%RUNS_DIR%\%RUN_ID%"
mkdir "%RUN_DIR%" >nul 2>&1 || (
    echo ERROR: No se pudo crear "%RUN_DIR%".
    exit /b 1
)
set "RUN_SUMMARY=%RUN_DIR%\summary.txt"
set "TESTS_STDOUT=%RUN_DIR%\tests_stdout.txt"
set "TESTS_STDERR=%RUN_DIR%\tests_stderr.txt"
set "GATE_STDOUT=%RUN_DIR%\gate_stdout.txt"
set "GATE_STDERR=%RUN_DIR%\gate_stderr.txt"
set "COVERAGE_HTML_DIR=%RUN_DIR%\coverage_html"
set "COVERAGE_TXT=%RUN_DIR%\coverage_report.txt"
>"%LAST_RUN_ID_FILE%" echo %RUN_ID%
exit /b 0

:run_step
set "STEP_NAME=%~1"
set "STEP_SCRIPT=%~2"
set "STEP_ARGS=%~3"
if defined STEP_ARGS if "%STEP_ARGS:~0,1%"=="\"" if "%STEP_ARGS:~-1%"=="\"" set "STEP_ARGS=%STEP_ARGS:~1,-1%"
set "STEP_STDOUT=%~4"
set "STEP_STDERR=%~5"
set "STEP_REASON=%~6"

set "CMDLINE=""%STEP_SCRIPT%"" %STEP_ARGS%"
echo [RUN_STEP] %STEP_NAME%: %CMDLINE%

call "%STEP_SCRIPT%" %STEP_ARGS% 1>"%STEP_STDOUT%" 2>"%STEP_STDERR%"
set "STEP_EXIT=%ERRORLEVEL%"

echo [RUN_STEP] %STEP_NAME% exit code: %STEP_EXIT%

if not "%STEP_EXIT%"=="0" (
    call :SET_ERROR_STATE "%STEP_NAME%" "!CMDLINE!" "%STEP_STDOUT%" "%STEP_STDERR%" "%STEP_EXIT%" "%STEP_REASON%"
    call :HANDLE_STEP_ERROR
    exit /b 1
)
exit /b 0

:SET_ERROR_STATE
set "LAST_ERROR_STEP=%~1"
set "LAST_ERROR_CMD=%~2"
set "LAST_ERROR_STDOUT=%~3"
set "LAST_ERROR_STDERR=%~4"
set "LAST_ERROR_EXIT=%~5"
set "LAST_ERROR_REASON=%~6"
set "RUN_STEP_FAILED=1"
exit /b 0

:HANDLE_STEP_ERROR
echo [ERROR] Paso fallido: %LAST_ERROR_STEP%
echo [ERROR] Comando ejecutado: %LAST_ERROR_CMD%
echo [ERROR] Exit code: %LAST_ERROR_EXIT%
if defined LAST_ERROR_REASON echo [ERROR] Motivo: %LAST_ERROR_REASON%
echo [ERROR] Log stdout: %LAST_ERROR_STDOUT%
echo [ERROR] Log stderr: %LAST_ERROR_STDERR%
if exist "%LAST_ERROR_STDERR%" (
    echo [ERROR] Primeras 60 lineas de stderr:
    set /a ERR_LINE_COUNT=0
    for /f "usebackq delims=" %%L in (`more +0 "%LAST_ERROR_STDERR%"`) do (
        if !ERR_LINE_COUNT! LSS 60 (
            echo %%L
            set /a ERR_LINE_COUNT+=1
        )
    )
)
if "%DEBUG_SANITY%"=="1" (
    echo [DEBUG] Sanity error state:
    echo [DEBUG] LAST_ERROR_STEP=%LAST_ERROR_STEP%
    echo [DEBUG] LAST_ERROR_CMD=%LAST_ERROR_CMD%
    echo [DEBUG] LAST_ERROR_EXIT=%LAST_ERROR_EXIT%
    echo [DEBUG] LAST_ERROR_STDOUT=%LAST_ERROR_STDOUT%
    echo [DEBUG] LAST_ERROR_STDERR=%LAST_ERROR_STDERR%
    echo [DEBUG] LAST_ERROR_REASON=%LAST_ERROR_REASON%
)
set "PAUSE_ALREADY_DONE=1"
pause
exit /b 0

:RUN_TESTS
set "TESTS_STATUS=NO_EJECUTADO"
set "TESTS_CODE=NO_EJECUTADO"
call :WRITE_TESTS_ENV
call :run_step "tests" "%TESTS_SCRIPT%" "" "%TESTS_STDOUT%" "%TESTS_STDERR%" "Fallo en ejecutar_tests.bat"
if errorlevel 1 (
    set "TESTS_STATUS=FAIL"
    set "TESTS_CODE=%LAST_ERROR_EXIT%"
    echo.
    echo ===== RESUMEN PYTEST ^(stdout^) =====
    if exist "%TESTS_STDOUT%" (
      findstr /i /c:"FAILED" /c:"ERROR" "%TESTS_STDOUT%"
      findstr /i /r "^[0-9][0-9]* failed" "%TESTS_STDOUT%"
      findstr /i /r "^[0-9][0-9]* passed" "%TESTS_STDOUT%"
    ) else (
      echo No existe %TESTS_STDOUT%
    )
    echo ==================================
    echo.
    exit /b %TESTS_CODE%
)
set "TESTS_STATUS=PASS"
set "TESTS_CODE=0"
call :GENERATE_COVERAGE_ARTIFACTS
exit /b 0

:RUN_GATE
set "GATE_STATUS=NO_EJECUTADO"
set "GATE_CODE=NO_EJECUTADO"
call :run_step "quality_gate" "%GATE_SCRIPT%" "" "%GATE_STDOUT%" "%GATE_STDERR%" "Fallo en quality_gate.bat"
if errorlevel 1 (
    set "GATE_STATUS=FAIL"
    set "GATE_CODE=%LAST_ERROR_EXIT%"
    exit /b %GATE_CODE%
)
set "GATE_STATUS=PASS"
set "GATE_CODE=0"
exit /b 0

:RUN_DEBUG_SELF_TEST
set "TESTS_STATUS=NO_EJECUTADO"
set "TESTS_CODE=NO_EJECUTADO"
call :run_step "dummy_fail" "%ComSpec%" "/c exit /b 1" "%TESTS_STDOUT%" "%TESTS_STDERR%" "Self-test dummy fail"
if errorlevel 1 (
    set "TESTS_STATUS=FAIL"
    set "TESTS_CODE=%LAST_ERROR_EXIT%"
    exit /b %TESTS_CODE%
)
set "TESTS_STATUS=PASS"
set "TESTS_CODE=0"
exit /b 0

:GENERATE_COVERAGE_ARTIFACTS
if not exist "%REPO_ROOT%\.coverage" exit /b 0
python -m coverage report -m >"%COVERAGE_TXT%" 2>&1
if not exist "%COVERAGE_HTML_DIR%" mkdir "%COVERAGE_HTML_DIR%" >nul 2>&1
python -m coverage html -d "%COVERAGE_HTML_DIR%" >>"%COVERAGE_TXT%" 2>&1
exit /b 0

:WRITE_SUMMARY
>"%RUN_SUMMARY%" echo MENU VALIDACION - EJECUCION %RUN_ID%
>>"%RUN_SUMMARY%" echo Fecha: %DATE% %TIME%
>>"%RUN_SUMMARY%" echo Carpeta raiz: %REPO_ROOT%
>>"%RUN_SUMMARY%" echo Opcion: %LAST_ACTION%
>>"%RUN_SUMMARY%" echo Comando tests: "%TESTS_SCRIPT%"
>>"%RUN_SUMMARY%" echo Resultado tests: %TESTS_STATUS% ^(exit %TESTS_CODE%^)
>>"%RUN_SUMMARY%" echo Resultado quality: %GATE_STATUS% ^(exit %GATE_CODE%^)
>>"%RUN_SUMMARY%" echo tests_stdout: %TESTS_STDOUT%
>>"%RUN_SUMMARY%" echo tests_stderr: %TESTS_STDERR%
>>"%RUN_SUMMARY%" echo gate_stdout: %GATE_STDOUT%
>>"%RUN_SUMMARY%" echo gate_stderr: %GATE_STDERR%
if exist "%COVERAGE_HTML_DIR%\index.html" >>"%RUN_SUMMARY%" echo coverage_html: %COVERAGE_HTML_DIR%\index.html
if defined LAST_ERROR_STEP (
    >>"%RUN_SUMMARY%" echo ERROR_STEP=%LAST_ERROR_STEP%
    >>"%RUN_SUMMARY%" echo ERROR_EXIT=%LAST_ERROR_EXIT%
    >>"%RUN_SUMMARY%" echo ERROR_REASON=%LAST_ERROR_REASON%
)
exit /b 0

:PUBLISH_LAST_SUMMARY
if defined RUN_SUMMARY copy /y "%RUN_SUMMARY%" "%SUMMARY_FILE%" >nul 2>&1
exit /b 0

:ENSURE_LOG_DIRS
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
if not exist "%RUNS_DIR%" mkdir "%RUNS_DIR%" >nul 2>&1
exit /b 0

:WRITE_MENU_EXECUTION_LOG
call :ENSURE_LOG_DIRS
set "EXEC_LOG_TS=%DATE% %TIME%"
>>"%SUMMARY_FILE%" echo [!EXEC_LOG_TS!] opcion=%~1 exitcode=%~2
exit /b 0

:WRITE_TESTS_ENV
call :ENSURE_LOG_DIRS
>"%TESTS_ENV_FILE%" echo [%DATE% %TIME%] Entorno previo a tests
>>"%TESTS_ENV_FILE%" echo python --version
python --version >>"%TESTS_ENV_FILE%" 2>&1
>>"%TESTS_ENV_FILE%" echo pip --version
pip --version >>"%TESTS_ENV_FILE%" 2>&1
>>"%TESTS_ENV_FILE%" echo where python
where python >>"%TESTS_ENV_FILE%" 2>&1
exit /b 0

:safe_open
set "SAFE_OPEN_TARGET=%~1"
if not defined SAFE_OPEN_TARGET (
    echo [ERROR] safe_open requiere ruta destino.
    exit /b 1
)
if not exist "%SAFE_OPEN_TARGET%" (
    echo [ERROR] No existe el fichero: "%SAFE_OPEN_TARGET%"
    exit /b 1
)
start "" "%SAFE_OPEN_TARGET%"
exit /b 0

:OPEN_LAST_COVERAGE_HTML
set "LAST_RUN_ID="
for /f "delims=" %%D in ('dir /b /ad /o-n "%RUNS_DIR%" 2^>nul') do if not defined LAST_RUN_ID set "LAST_RUN_ID=%%D"
if not defined LAST_RUN_ID (
    echo No hay ejecuciones en "%RUNS_DIR%".
    set "PAUSE_ALREADY_DONE=1"
    pause
    exit /b 1
)
set "LAST_COV_DIR=%RUNS_DIR%\%LAST_RUN_ID%\coverage_html"
set "LAST_COV_INDEX=%LAST_COV_DIR%\index.html"
if not exist "%LAST_COV_INDEX%" (
    echo [ERROR] No existe coverage index.html.
    echo [ERROR] Ruta buscada: "%LAST_COV_INDEX%"
    echo [ERROR] Carpeta run detectada: "%RUNS_DIR%\%LAST_RUN_ID%"
    if exist "%LAST_COV_DIR%" (
        dir /b "%LAST_COV_DIR%" >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] coverage_html existe pero esta vacia.
        ) else (
            echo [INFO] coverage_html existe pero no contiene index.html.
        )
    ) else (
        echo [ERROR] coverage_html no existe.
    )
    set "PAUSE_ALREADY_DONE=1"
    pause
    exit /b 1
)
call :safe_open "%LAST_COV_INDEX%"
exit /b %ERRORLEVEL%

:PRINT_RESULTS
echo.
if defined RUN_ID (
    echo Resumen ultimo run: logs\runs\%RUN_ID%
) else (
    echo Resumen ultimo run: [sin run activo]
)
echo TESTS: %TESTS_STATUS% ^(exit %TESTS_CODE%^)
echo QUALITY GATE: %GATE_STATUS% ^(exit %GATE_CODE%^)
echo Resumen: logs\menu_ultima_ejecucion.txt
exit /b 0

:FINALIZE_ACTION
call :PRINT_RESULTS
echo Abre logs con la opcion 4.
if not "%PAUSE_ALREADY_DONE%"=="1" pause
exit /b 0

:END
call :WRITE_MENU_EXECUTION_LOG "Salir" "%SCRIPT_EXIT_CODE%"
echo Saliendo del menu de validacion.
exit /b %SCRIPT_EXIT_CODE%
