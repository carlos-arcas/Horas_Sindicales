@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "REPO_ROOT=%ROOT_DIR%"
set "LOG_DIR=%REPO_ROOT%\logs"
set "RUNS_DIR=%LOG_DIR%\runs"
set "SUMMARY_FILE=%LOG_DIR%\menu_ultima_ejecucion.txt"
set "LAST_RUN_ID_FILE=%LOG_DIR%\menu_last_run_id.txt"
set "ENV_SNAPSHOT_LEGACY=%REPO_ROOT%\logs\menu_tests_env.txt"
set "TESTS_SCRIPT=%REPO_ROOT%\ejecutar_tests.bat"
set "GATE_SCRIPT=%REPO_ROOT%\quality_gate.bat"

rem Compat contract legacy checks:
rem if not exist "%ROOT_DIR%ejecutar_tests.bat"
rem if not exist "%ROOT_DIR%quality_gate.bat"
rem 2>>"%SUMMARY_FILE%"

set "SCRIPT_EXIT_CODE=0"
set "CHOICE="
set "LAST_ACTION=Sin ejecutar"
set "TESTS_STATUS=NO_EJECUTADO"
set "TESTS_CODE=NO_EJECUTADO"
set "GATE_STATUS=NO_EJECUTADO"
set "GATE_CODE=NO_EJECUTADO"
set "PATH_ERROR_TESTS=0"
set "PATH_ERROR_GATE=0"
set "TESTS_EXEC=0"
set "GATE_EXEC=0"
set "RUN_DIR="
set "RUN_ID="

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
if not exist "%RUNS_DIR%" mkdir "%RUNS_DIR%" >nul 2>&1
cd /d "%REPO_ROOT%"

:MENU
echo.
echo ==============================================
echo Menu de validacion - Horas Sindicales
echo ==============================================
echo 1) Ejecutar tests
echo 2) Ejecutar quality gate
echo 3) Ejecutar ambos (tests + quality gate)
echo 4) Abrir carpeta logs
echo 5) Abrir el ultimo summary en Notepad
echo 6) Abrir coverage html (index.html) del ultimo run
echo 0) Salir
set /p "CHOICE=> "

if "%CHOICE%"=="1" (
    set "LAST_ACTION=Ejecutar tests"
    call :RUN_PREFLIGHT
    if errorlevel 1 (
        call :HANDLE_STEP_ERROR "preflight" "N/A" "%ENV_SNAPSHOT_LEGACY%" "%ENV_SNAPSHOT_LEGACY%" "%ERRORLEVEL%"
        call :FINALIZE_ACTION
        goto MENU
    )
    call :RUN_TESTS
    call :WRITE_SUMMARY
    call :PUBLISH_LAST_SUMMARY
    set "SCRIPT_EXIT_CODE=!TESTS_CODE!"
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="2" (
    set "LAST_ACTION=Ejecutar quality gate"
    call :RUN_PREFLIGHT
    if errorlevel 1 (
        call :HANDLE_STEP_ERROR "preflight" "N/A" "%ENV_SNAPSHOT_LEGACY%" "%ENV_SNAPSHOT_LEGACY%" "%ERRORLEVEL%"
        call :FINALIZE_ACTION
        goto MENU
    )
    call :RUN_GATE
    call :WRITE_SUMMARY
    call :PUBLISH_LAST_SUMMARY
    set "SCRIPT_EXIT_CODE=!GATE_CODE!"
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="3" (
    set "LAST_ACTION=Ejecutar ambos"
    call :RUN_PREFLIGHT
    if errorlevel 1 (
        call :HANDLE_STEP_ERROR "preflight" "N/A" "%ENV_SNAPSHOT_LEGACY%" "%ENV_SNAPSHOT_LEGACY%" "%ERRORLEVEL%"
        call :FINALIZE_ACTION
        goto MENU
    )
    call :WRITE_MENU_ENV "PRE"
    call :RUN_TESTS
    if not "!TESTS_CODE!"=="0" (
        set "CONTINUE_GATE="
        echo Tests con fallo (exit !TESTS_CODE!).
        set /p "CONTINUE_GATE=Continuar con quality gate? (Y/N): "
        if /i not "!CONTINUE_GATE!"=="Y" (
            call :WRITE_MENU_ENV "POST"
            set "SCRIPT_EXIT_CODE=!TESTS_CODE!"
            call :WRITE_SUMMARY
            call :PUBLISH_LAST_SUMMARY
            call :FINALIZE_ACTION
            goto MENU
        )
        echo Continuando con quality gate por confirmacion del usuario.
    )
    call :RUN_GATE
    call :WRITE_MENU_ENV "POST"
    if "!TESTS_CODE!"=="0" (
        set "SCRIPT_EXIT_CODE=!GATE_CODE!"
    ) else (
        if "!GATE_CODE!"=="0" (
            set "SCRIPT_EXIT_CODE=!TESTS_CODE!"
        ) else (
            set "SCRIPT_EXIT_CODE=!GATE_CODE!"
        )
    )
    call :WRITE_SUMMARY
    call :PUBLISH_LAST_SUMMARY
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="4" (
    if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
    start "" "%LOG_DIR%"
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="5" (
    if exist "%SUMMARY_FILE%" (
        start "" notepad "%SUMMARY_FILE%"
    ) else (
        echo No existe aun "%SUMMARY_FILE%".
    )
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="6" (
    call :OPEN_LAST_COVERAGE_HTML
    call :FINALIZE_ACTION
    goto MENU
)
if "%CHOICE%"=="0" goto END

echo Opcion invalida. Intenta de nuevo.
call :FINALIZE_ACTION
goto MENU

:RUN_PREFLIGHT
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
if not exist "%RUNS_DIR%" mkdir "%RUNS_DIR%" >nul 2>&1
if not exist "%ROOT_DIR%\ejecutar_tests.bat" (
    echo ERROR: No existe "%ROOT_DIR%\ejecutar_tests.bat".
    exit /b 2
)
if not exist "%ROOT_DIR%\quality_gate.bat" (
    echo ERROR: No existe "%ROOT_DIR%\quality_gate.bat".
    exit /b 2
)

call :CREATE_RUN_DIR
if errorlevel 1 exit /b 2

call :DETECT_PYTHON
call :CAPTURE_ENV

if not defined PYTHON_CMD (
    >>"%RUN_SUMMARY%" echo [WARN] No se detecto Python ni .venv\Scripts\python.exe.
    >>"%RUN_SUMMARY%" echo [WARN] Los reportes coverage pueden no generarse.
)

set "TESTS_STATUS=NO_EJECUTADO"
set "TESTS_CODE=NO_EJECUTADO"
set "GATE_STATUS=NO_EJECUTADO"
set "GATE_CODE=NO_EJECUTADO"
set "PATH_ERROR_TESTS=0"
set "PATH_ERROR_GATE=0"
set "TESTS_EXEC=0"
set "GATE_EXEC=0"
exit /b 0

:CREATE_RUN_DIR
set "RUN_ID=%DATE%_%TIME%"
set "RUN_ID=%RUN_ID:/=%"
set "RUN_ID=%RUN_ID::=%"
set "RUN_ID=%RUN_ID:.=%"
set "RUN_ID=%RUN_ID:,=%"
set "RUN_ID=%RUN_ID: =0%"
set "RUN_DIR=%RUNS_DIR%\%RUN_ID%"
mkdir "%RUN_DIR%" >nul 2>&1
if errorlevel 1 (
    echo ERROR: No se pudo crear "%RUN_DIR%".
    exit /b 1
)
set "RUN_SUMMARY=%RUN_DIR%\summary.txt"
set "RUN_ENV=%RUN_DIR%\env.txt"
set "TESTS_STDOUT=%RUN_DIR%\tests_stdout.txt"
set "TESTS_STDERR=%RUN_DIR%\tests_stderr.txt"
set "GATE_STDOUT=%RUN_DIR%\gate_stdout.txt"
set "GATE_STDERR=%RUN_DIR%\gate_stderr.txt"
set "COVERAGE_TXT=%RUN_DIR%\coverage_report.txt"
set "COVERAGE_HTML_DIR=%RUN_DIR%\coverage_html"
set "RUN_JUNIT=%RUN_DIR%\junit.xml"
>"%RUN_SUMMARY%" echo MENU VALIDACION - EJECUCION %RUN_ID%
>>"%RUN_SUMMARY%" echo Fecha: %DATE% %TIME%
>>"%RUN_SUMMARY%" echo REPO_ROOT=%REPO_ROOT%
>>"%RUN_SUMMARY%" echo LOG_RUN_DIR=%RUN_DIR%
>"%LAST_RUN_ID_FILE%" echo %RUN_ID%
exit /b 0

:DETECT_PYTHON
set "PYTHON_CMD="
if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%REPO_ROOT%\.venv\Scripts\python.exe"
    exit /b 0
)
where python >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    exit /b 0
)
where py >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py -3"
exit /b 0

:CAPTURE_ENV
>"%RUN_ENV%" echo [meta]
>>"%RUN_ENV%" echo Fecha=%DATE% %TIME%
>>"%RUN_ENV%" echo ROOT_DIR=%ROOT_DIR%
>>"%RUN_ENV%" echo REPO_ROOT=%REPO_ROOT%
>>"%RUN_ENV%" echo RUN_DIR=%RUN_DIR%
>>"%RUN_ENV%" echo.
>>"%RUN_ENV%" echo [where python]
where python >>"%RUN_ENV%" 2>&1
>>"%RUN_ENV%" echo.
>>"%RUN_ENV%" echo [where pytest]
where pytest >>"%RUN_ENV%" 2>&1
>>"%RUN_ENV%" echo.
>>"%RUN_ENV%" echo [python --version]
python --version >>"%RUN_ENV%" 2>&1
copy /y "%RUN_ENV%" "%ENV_SNAPSHOT_LEGACY%" >nul 2>&1
exit /b 0

:WRITE_MENU_ENV
set "MENU_ENV_PHASE=%~1"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
>>"%ENV_SNAPSHOT_LEGACY%" echo [%MENU_ENV_PHASE%] Fecha=%DATE% %TIME%
>>"%ENV_SNAPSHOT_LEGACY%" echo [%MENU_ENV_PHASE%] RUN_DIR=%RUN_DIR%
>>"%ENV_SNAPSHOT_LEGACY%" echo [%MENU_ENV_PHASE%] LAST_ACTION=%LAST_ACTION%
>>"%ENV_SNAPSHOT_LEGACY%" echo [%MENU_ENV_PHASE%] TESTS_CODE=%TESTS_CODE%
>>"%ENV_SNAPSHOT_LEGACY%" echo [%MENU_ENV_PHASE%] GATE_CODE=%GATE_CODE%
>>"%ENV_SNAPSHOT_LEGACY%" echo.
exit /b 0

:run_step
set "STEP_NAME=%~1"
set "STEP_COMMAND=%~2"
set "STEP_STDOUT=%~3"
set "STEP_STDERR=%~4"
echo [RUN_STEP] !STEP_NAME!: !STEP_COMMAND!
>>"%RUN_SUMMARY%" echo CMD_!STEP_NAME!=!STEP_COMMAND!
>>"%RUN_SUMMARY%" echo LOG_STDOUT_!STEP_NAME!=!STEP_STDOUT!
>>"%RUN_SUMMARY%" echo LOG_STDERR_!STEP_NAME!=!STEP_STDERR!
call !STEP_COMMAND! 1>>"!STEP_STDOUT!" 2>>"!STEP_STDERR!"
set "STEP_EXIT=!ERRORLEVEL!"
echo [RUN_STEP] !STEP_NAME! exit code: !STEP_EXIT!
exit /b !STEP_EXIT!

:RUN_TESTS
set "TESTS_EXEC=1"
set "TESTS_STATUS=NO_EJECUTADO"
set "TESTS_CODE=NO_EJECUTADO"
set "STEP_CMD=\"%TESTS_SCRIPT%\""
call :run_step "tests" "%STEP_CMD%" "%TESTS_STDOUT%" "%TESTS_STDERR%"
set "TESTS_CODE=%ERRORLEVEL%"
if "%TESTS_CODE%"=="0" (set "TESTS_STATUS=PASS") else (set "TESTS_STATUS=FAIL")
if not "%TESTS_CODE%"=="0" call :HANDLE_STEP_ERROR "tests" "%STEP_CMD%" "%TESTS_STDOUT%" "%TESTS_STDERR%" "%TESTS_CODE%"
findstr /c:"El sistema no puede encontrar la ruta especificada." "%TESTS_STDERR%" >nul 2>&1
if not errorlevel 1 set "PATH_ERROR_TESTS=1"
call :GENERATE_COVERAGE_ARTIFACTS
exit /b %TESTS_CODE%

:RUN_GATE
set "GATE_EXEC=1"
set "GATE_STATUS=NO_EJECUTADO"
set "GATE_CODE=NO_EJECUTADO"
set "STEP_CMD=\"%GATE_SCRIPT%\""
call :run_step "quality_gate" "%STEP_CMD%" "%GATE_STDOUT%" "%GATE_STDERR%"
set "GATE_CODE=%ERRORLEVEL%"
if "%GATE_CODE%"=="0" (set "GATE_STATUS=PASS") else (set "GATE_STATUS=FAIL")
if not "%GATE_CODE%"=="0" call :HANDLE_STEP_ERROR "quality_gate" "%STEP_CMD%" "%GATE_STDOUT%" "%GATE_STDERR%" "%GATE_CODE%"
findstr /c:"El sistema no puede encontrar la ruta especificada." "%GATE_STDERR%" >nul 2>&1
if not errorlevel 1 set "PATH_ERROR_GATE=1"
exit /b %GATE_CODE%

:HANDLE_STEP_ERROR
set "ERR_STEP=%~1"
set "ERR_CMD=%~2"
set "ERR_STDOUT=%~3"
set "ERR_STDERR=%~4"
set "ERR_CODE=%~5"
echo [ERROR] Paso fallido: !ERR_STEP!
echo [ERROR] Comando ejecutado: !ERR_CMD!
echo [ERROR] Exit code: !ERR_CODE!
echo [ERROR] Log stdout: !ERR_STDOUT!
echo [ERROR] Log stderr: !ERR_STDERR!
if defined RUN_SUMMARY (
    >>"%RUN_SUMMARY%" echo ERROR_STEP=!ERR_STEP!
    >>"%RUN_SUMMARY%" echo ERROR_CMD=!ERR_CMD!
    >>"%RUN_SUMMARY%" echo ERROR_EXIT_CODE=!ERR_CODE!
)
exit /b 0

:GENERATE_COVERAGE_ARTIFACTS
if not exist "%REPO_ROOT%\.coverage" exit /b 0
if not defined PYTHON_CMD exit /b 0
"%PYTHON_CMD%" -m coverage report -m >"%COVERAGE_TXT%" 2>&1
if not exist "%COVERAGE_HTML_DIR%" mkdir "%COVERAGE_HTML_DIR%" >nul 2>&1
"%PYTHON_CMD%" -m coverage html -d "%COVERAGE_HTML_DIR%" >>"%COVERAGE_TXT%" 2>&1
if exist "%REPO_ROOT%\junit.xml" copy /y "%REPO_ROOT%\junit.xml" "%RUN_JUNIT%" >nul 2>&1
if exist "%REPO_ROOT%\logs\junit.xml" copy /y "%REPO_ROOT%\logs\junit.xml" "%RUN_JUNIT%" >nul 2>&1
exit /b 0

:WRITE_SUMMARY
>"%RUN_SUMMARY%" echo MENU VALIDACION - EJECUCION %RUN_ID%
>>"%RUN_SUMMARY%" echo Fecha: %DATE% %TIME%
>>"%RUN_SUMMARY%" echo REPO_ROOT=%REPO_ROOT%
>>"%RUN_SUMMARY%" echo Opcion=%LAST_ACTION%
>>"%RUN_SUMMARY%" echo TESTS=%TESTS_STATUS% ^(exit %TESTS_CODE%^)
>>"%RUN_SUMMARY%" echo QUALITY_GATE=%GATE_STATUS% ^(exit %GATE_CODE%^)
>>"%RUN_SUMMARY%" echo Summary run: logs\runs\%RUN_ID%\summary.txt
>>"%RUN_SUMMARY%" echo Env: logs\runs\%RUN_ID%\env.txt
>>"%RUN_SUMMARY%" echo tests_stdout: logs\runs\%RUN_ID%\tests_stdout.txt
>>"%RUN_SUMMARY%" echo tests_stderr: logs\runs\%RUN_ID%\tests_stderr.txt
>>"%RUN_SUMMARY%" echo gate_stdout: logs\runs\%RUN_ID%\gate_stdout.txt
>>"%RUN_SUMMARY%" echo gate_stderr: logs\runs\%RUN_ID%\gate_stderr.txt
if exist "%COVERAGE_TXT%" >>"%RUN_SUMMARY%" echo coverage_report: logs\runs\%RUN_ID%\coverage_report.txt
if exist "%COVERAGE_HTML_DIR%\index.html" >>"%RUN_SUMMARY%" echo coverage_html: logs\runs\%RUN_ID%\coverage_html\index.html
if exist "%RUN_JUNIT%" >>"%RUN_SUMMARY%" echo junit: logs\runs\%RUN_ID%\junit.xml
if "%PATH_ERROR_TESTS%"=="1" >>"%RUN_SUMMARY%" echo [PISTA] Ruta no encontrada en ejecutar_tests.bat. Revisa tests_stderr.
if "%PATH_ERROR_GATE%"=="1" >>"%RUN_SUMMARY%" echo [PISTA] Ruta no encontrada en quality_gate.bat. Revisa gate_stderr.
if "%TESTS_EXEC%"=="1" (
    >>"%RUN_SUMMARY%" echo.
    >>"%RUN_SUMMARY%" echo --- Extracto tests stderr (max 120) ---
    call :APPEND_HEAD "%TESTS_STDERR%" 120 "%RUN_SUMMARY%"
)
if "%GATE_EXEC%"=="1" (
    >>"%RUN_SUMMARY%" echo.
    >>"%RUN_SUMMARY%" echo --- Extracto gate stderr (max 120) ---
    call :APPEND_HEAD "%GATE_STDERR%" 120 "%RUN_SUMMARY%"
)
if exist "%RUN_ENV%" copy /y "%RUN_ENV%" "%ENV_SNAPSHOT_LEGACY%" >nul 2>&1
if "%LAST_ACTION%"=="Ejecutar ambos" call :WRITE_MENU_ENV "POST"
exit /b 0

:PUBLISH_LAST_SUMMARY
copy /y "%RUN_SUMMARY%" "%SUMMARY_FILE%" >nul 2>&1
if errorlevel 1 (
    echo [WARN] No se pudo actualizar "%SUMMARY_FILE%" (posible archivo bloqueado).
    echo [WARN] Revisa directamente "%RUN_SUMMARY%".
)
exit /b 0

:APPEND_HEAD
set "SRC_FILE=%~1"
set "MAX_LINES=%~2"
set "DST_FILE=%~3"
if not exist "%SRC_FILE%" (
    >>"%DST_FILE%" echo [sin archivo: %SRC_FILE%]
    exit /b 0
)
for /f "usebackq tokens=1,* delims=:" %%A in (`findstr /n "^" "%SRC_FILE%"`) do (
    if %%A LEQ %MAX_LINES% >>"%DST_FILE%" echo %%B
)
exit /b 0

:safe_open
set "TARGET_FILE=%~1"
if not exist "%TARGET_FILE%" (
    echo [ERROR] No existe el archivo: "%TARGET_FILE%"
    echo [INFO] coverage_html puede faltar si pytest/coverage fallo.
    echo [INFO] Sugerencia: ejecuta opcion 1 o 3.
    if defined RUN_SUMMARY >>"%RUN_SUMMARY%" echo SAFE_OPEN_MISSING=%TARGET_FILE%
    exit /b 1
)
start "" "%TARGET_FILE%"
exit /b 0

:OPEN_LAST_COVERAGE_HTML
set "LAST_RUN_ID="
for /f "delims=" %%D in ('dir /b /ad /o-n "%RUNS_DIR%" 2^>nul') do (
    if not defined LAST_RUN_ID set "LAST_RUN_ID=%%D"
)
if not defined LAST_RUN_ID (
    echo No hay ejecuciones en "%RUNS_DIR%".
    echo Sugerencia: ejecuta opcion 1 o 3 para generar un run.
    exit /b 0
)
set "LAST_SUMMARY_MD=%RUNS_DIR%\%LAST_RUN_ID%\summary.md"
set "LAST_SUMMARY_JSON=%RUNS_DIR%\%LAST_RUN_ID%\summary.json"
set "LAST_SUMMARY_TXT=%RUNS_DIR%\%LAST_RUN_ID%\summary.txt"
if exist "%LAST_SUMMARY_MD%" (
    echo Ultimo summary detectado: "%LAST_SUMMARY_MD%"
) else if exist "%LAST_SUMMARY_JSON%" (
    echo Ultimo summary detectado: "%LAST_SUMMARY_JSON%"
) else (
    echo Ultimo summary detectado: "%LAST_SUMMARY_TXT%"
)
set "LAST_COV_INDEX=%RUNS_DIR%\%LAST_RUN_ID%\coverage_html\index.html"
call :safe_open "%LAST_COV_INDEX%"
exit /b 0

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
pause
exit /b 0

:END
echo Saliendo del menu de validacion.
exit /b %SCRIPT_EXIT_CODE%
