@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "root_dir=%~dp0"
if "%root_dir:~-1%"=="\" set "root_dir=%root_dir:~0,-1%"
set "repo_root=%root_dir%"
set "log_dir=%repo_root%\logs"
set "runs_dir=%log_dir%\runs"
set "summary_file=%log_dir%\menu_ultima_ejecucion.txt"
set "menu_env_file=%log_dir%\menu_tests_env.txt"
rem logs\menu_tests_env.txt
set "last_run_id_file=%log_dir%\menu_last_run_id.txt"
set "tests_script=%repo_root%\ejecutar_tests.bat"
set "gate_script=%repo_root%\quality_gate.bat"

set "script_exit_code=0"
set "choice="
set "last_action=Sin ejecutar"
set "tests_status=NO_EJECUTADO"
set "tests_code=NO_EJECUTADO"
set "gate_status=NO_EJECUTADO"
set "gate_code=NO_EJECUTADO"
set "run_dir="
set "run_id="
set "run_step_failed=0"
set "last_error_step="
set "last_error_reason="
set "last_error_stdout="
set "last_error_stderr="
set "last_error_cmd="
set "last_error_exit="
set "pause_already_done=0"
set "debug_sanity=0"

if not exist "%log_dir%" mkdir "%log_dir%" >nul 2>&1
if not exist "%runs_dir%" mkdir "%runs_dir%" >nul 2>&1
cd /d "%repo_root%"

:menu
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
echo 9) [debug] Self-test run_step con dummy_fail
echo 0) Salir
set /p "choice=> "

if "%choice%"=="1" (
    set "last_action=Ejecutar tests"
    set "pause_already_done=0"
    call :run_preflight || (
        call :finalize_action
        goto menu
    )
    call :run_tests
    call :write_summary
    call :publish_last_summary
    set "script_exit_code=!tests_code!"
    call :finalize_action
    goto menu
)
if "%choice%"=="2" (
    set "last_action=Ejecutar quality gate"
    set "pause_already_done=0"
    call :run_preflight || (
        call :finalize_action
        goto menu
    )
    call :run_gate
    echo QUALITY GATE: !gate_status! exit code !gate_code!
    call :write_summary
    call :publish_last_summary
    set "script_exit_code=!gate_code!"
    call :finalize_action
    goto menu
)
if "%choice%"=="3" (
    set "last_action=Ejecutar ambos"
    set "pause_already_done=0"
    call :run_preflight || (
        call :finalize_action
        goto menu
    )
    call :run_tests
    if not "!tests_code!"=="0" (
        set "gate_status=NO_EJECUTADO"
        set "gate_code=NO_EJECUTADO"
        call :write_summary
        call :publish_last_summary
        set "script_exit_code=!tests_code!"
        call :finalize_action
        goto menu
    )
    call :run_gate
    call :write_summary
    call :publish_last_summary
    set "script_exit_code=!gate_code!"
    call :finalize_action
    goto menu
)
if "%choice%"=="4" (
    set "pause_already_done=0"
    if not exist "%log_dir%" mkdir "%log_dir%" >nul 2>&1
    call :safe_open "%log_dir%"
    call :finalize_action
    goto menu
)
if "%choice%"=="5" (
    set "pause_already_done=0"
    if exist "%summary_file%" (
        start "" notepad "%summary_file%"
    ) else (
        echo No existe aun "%summary_file%".
    )
    call :finalize_action
    goto menu
)
if "%choice%"=="6" (
    set "pause_already_done=0"
    call :OPEN_LAST_COVERAGE_HTML
    call :finalize_action
    goto menu
)
if "%choice%"=="9" (
    set "last_action=Debug self-test run_step"
    set "pause_already_done=0"
    set "debug_sanity=1"
    call :run_preflight || (
        set "debug_sanity=0"
        call :finalize_action
        goto menu
    )
    call :run_debug_self_test
    set "debug_sanity=0"
    call :write_summary
    call :publish_last_summary
    set "script_exit_code=!tests_code!"
    call :finalize_action
    goto menu
)
if "%choice%"=="0" goto end

echo Opcion invalida. Intenta de nuevo.
call :finalize_action
goto menu

:run_preflight
if not exist "%log_dir%" mkdir "%log_dir%" >nul 2>&1
if not exist "%runs_dir%" mkdir "%runs_dir%" >nul 2>&1
if not exist "%root_dir%ejecutar_tests.bat" (
    call :set_error_state "preflight" "" "%summary_file%" "%summary_file%" "2" "No existe ejecutar_tests.bat"
    call :handle_step_error
    exit /b 1
)
if not exist "%root_dir%quality_gate.bat" (
    call :set_error_state "preflight" "" "%summary_file%" "%summary_file%" "2" "No existe quality_gate.bat"
    call :handle_step_error
    exit /b 1
)
call :create_run_dir || exit /b 1
call :write_menu_env "pre"
set "tests_status=NO_EJECUTADO"
set "tests_code=NO_EJECUTADO"
set "gate_status=NO_EJECUTADO"
set "gate_code=NO_EJECUTADO"
set "run_step_failed=0"
set "last_error_step="
set "last_error_reason="
set "last_error_stdout="
set "last_error_stderr="
set "last_error_cmd="
set "last_error_exit="
exit /b 0

:create_run_dir
set "run_id=%DATE%_%TIME%"
set "run_id=%run_id:/=%"
set "run_id=%run_id::=%"
set "run_id=%run_id:.=%"
set "run_id=%run_id:,=%"
set "run_id=%run_id: =0%"
set "run_dir=%runs_dir%\%run_id%"
mkdir "%run_dir%" >nul 2>&1 || (
    echo ERROR: No se pudo crear "%run_dir%".
    exit /b 1
)
set "run_summary=%run_dir%\summary.txt"
set "tests_stdout=%run_dir%\tests_stdout.txt"
set "tests_stderr=%run_dir%\tests_stderr.txt"
set "gate_stdout=%run_dir%\gate_stdout.txt"
set "gate_stderr=%run_dir%\gate_stderr.txt"
set "coverage_dir=%run_dir%\coverage_html"
set "coverage_index=%coverage_dir%\index.html"
>"%last_run_id_file%" echo %run_id%
exit /b 0

:write_menu_env
set "env_mode=%~1"
>>"%menu_env_file%" echo ===============================
>>"%menu_env_file%" echo mode=%env_mode% date=%date% time=%time%
>>"%menu_env_file%" echo root=%root_dir%
>>"%menu_env_file%" echo repo=%repo_root%
>>"%menu_env_file%" echo logs=%log_dir%
>>"%menu_env_file%" echo run_id=%run_id%
>>"%menu_env_file%" echo action=%last_action%
>>"%menu_env_file%" echo -- where python --
where python >>"%menu_env_file%" 2>>"%summary_file%"
>>"%menu_env_file%" echo -- where pytest --
where pytest >>"%menu_env_file%" 2>>"%summary_file%"
>>"%menu_env_file%" echo -- python --version --
python --version >>"%menu_env_file%" 2>>"%summary_file%"
exit /b 0

:run_step
set "step_name=%~1"
set "step_script=%~2"
set "step_args=%~3"
if defined step_args if "%step_args:~0,1%"=="\"" if "%step_args:~-1%"=="\"" set "step_args=%step_args:~1,-1%"
set "step_stdout=%~4"
set "step_stderr=%~5"
set "step_reason=%~6"
set "step_cmd_display=\"%step_script%\" %step_args%"

echo [run_step] %step_name%: %step_cmd_display%

call "%step_script%" %step_args% 1>"%step_stdout%" 2>"%step_stderr%"
set "step_exit=%ERRORLEVEL%"

echo [run_step] %step_name% exit code: %step_exit%

if not "%step_exit%"=="0" (
    call :set_error_state "%step_name%" "%step_cmd_display%" "%step_stdout%" "%step_stderr%" "%step_exit%" "%step_reason%"
    call :handle_step_error
    exit /b 1
)
exit /b 0

:set_error_state
set "last_error_step=%~1"
set "last_error_cmd=%~2"
set "last_error_stdout=%~3"
set "last_error_stderr=%~4"
set "last_error_exit=%~5"
set "last_error_reason=%~6"
set "run_step_failed=1"
exit /b 0

:handle_step_error
echo [ERROR] Paso fallido: %last_error_step%
echo [ERROR] Comando ejecutado: %last_error_cmd%
echo [ERROR] Exit code: %last_error_exit%
if defined last_error_reason echo [ERROR] Motivo: %last_error_reason%
echo [ERROR] Log stdout: %last_error_stdout%
echo [ERROR] Log stderr: %last_error_stderr%
if exist "%last_error_stderr%" (
    echo [ERROR] Primeras 60 lineas de stderr:
    set /a err_line_count=0
    for /f "usebackq delims=" %%L in (`more +0 "%last_error_stderr%"`) do (
        if !err_line_count! LSS 60 (
            echo %%L
            set /a err_line_count+=1
        )
    )
)
if "%debug_sanity%"=="1" (
    echo [DEBUG] Sanity error state:
    echo [DEBUG] last_error_step=%last_error_step%
    echo [DEBUG] last_error_cmd=%last_error_cmd%
    echo [DEBUG] last_error_exit=%last_error_exit%
    echo [DEBUG] last_error_stdout=%last_error_stdout%
    echo [DEBUG] last_error_stderr=%last_error_stderr%
    echo [DEBUG] last_error_reason=%last_error_reason%
)
set "pause_already_done=1"
pause
exit /b 0

:run_tests
set "tests_status=NO_EJECUTADO"
set "tests_code=NO_EJECUTADO"
call :run_step "tests" "%tests_script%" "" "%tests_stdout%" "%tests_stderr%" "Fallo en ejecutar_tests.bat"
if errorlevel 1 (
    set "tests_status=FAIL"
    set "tests_code=%last_error_exit%"
    echo.
    echo ===== RESUMEN PYTEST (stdout) =====
    if exist "%tests_stdout%" (
      findstr /i /c:"FAILED" /c:"ERROR" "%tests_stdout%"
      findstr /i /r "^[0-9][0-9]* failed" "%tests_stdout%"
      findstr /i /r "^[0-9][0-9]* passed" "%tests_stdout%"
    ) else (
      echo No existe %tests_stdout%
    )
    echo ==================================
    echo.
    call :write_menu_env "post"
    exit /b %tests_code%
)
set "tests_status=PASS"
set "tests_code=0"
call :write_menu_env "post"
exit /b 0

:run_gate
set "gate_status=NO_EJECUTADO"
set "gate_code=NO_EJECUTADO"
call :run_step "quality_gate" "%gate_script%" "" "%gate_stdout%" "%gate_stderr%" "Fallo en quality_gate.bat"
if errorlevel 1 (
    set "gate_status=FAIL"
    set "gate_code=%last_error_exit%"
    exit /b %gate_code%
)
set "gate_status=PASS"
set "gate_code=0"
exit /b 0

:run_debug_self_test
set "tests_status=NO_EJECUTADO"
set "tests_code=NO_EJECUTADO"
call :run_step "dummy_fail" "%ComSpec%" "/c exit /b 1" "%tests_stdout%" "%tests_stderr%" "Self-test dummy fail"
if errorlevel 1 (
    set "tests_status=FAIL"
    set "tests_code=%last_error_exit%"
    exit /b %tests_code%
)
set "tests_status=PASS"
set "tests_code=0"
exit /b 0

:write_summary
>"%run_summary%" echo MENU VALIDACION - EJECUCION %run_id%
>>"%run_summary%" echo Fecha: %DATE% %TIME%
>>"%run_summary%" echo Carpeta raiz: %repo_root%
>>"%run_summary%" echo Opcion: %last_action%
>>"%run_summary%" echo Comando tests: "%tests_script%"
>>"%run_summary%" echo Resultado tests: %tests_status% (exit %tests_code%)
>>"%run_summary%" echo Resultado quality: %gate_status% (exit %gate_code%)
>>"%run_summary%" echo tests_stdout: %tests_stdout%
>>"%run_summary%" echo tests_stderr: %tests_stderr%
>>"%run_summary%" echo gate_stdout: %gate_stdout%
>>"%run_summary%" echo gate_stderr: %gate_stderr%
if exist "%coverage_index%" >>"%run_summary%" echo coverage_index: %coverage_index%
if defined last_error_step (
    >>"%run_summary%" echo ERROR_STEP=%last_error_step%
    >>"%run_summary%" echo ERROR_EXIT=%last_error_exit%
    >>"%run_summary%" echo ERROR_REASON=%last_error_reason%
)
exit /b 0

:publish_last_summary
if defined run_summary copy /y "%run_summary%" "%summary_file%" >nul 2>&1
exit /b 0

:OPEN_LAST_COVERAGE_HTML
set "last_run_id="
for /f "delims=" %%D in ('dir /b /ad /o-n "%runs_dir%" 2^>nul') do if not defined last_run_id set "last_run_id=%%D"
if not defined last_run_id (
    echo No hay ejecuciones en "%runs_dir%".
    set "pause_already_done=1"
    pause
    exit /b 1
)
set "last_cov_dir=%runs_dir%\%last_run_id%\coverage_html"
set "last_cov_index=%last_cov_dir%\index.html"
if not exist "%last_cov_index%" (
    echo [ERROR] No existe index.html del ultimo run.
    echo [ERROR] Ruta buscada: "%last_cov_index%"
    set "pause_already_done=1"
    pause
    exit /b 1
)
call :safe_open "%last_cov_index%"
exit /b 0

:safe_open
set "open_target=%~1"
if not exist "%open_target%" exit /b 1
start "" "%open_target%"
exit /b 0

:print_results
echo.
if defined run_id (
    echo Resumen ultimo run: logs\runs\%run_id%
) else (
    echo Resumen ultimo run: [sin run activo]
)
echo TESTS: %tests_status% (exit %tests_code%)
echo QUALITY GATE: %gate_status% (exit %gate_code%)
echo Resumen: logs\menu_ultima_ejecucion.txt
exit /b 0

:finalize_action
call :print_results
echo Abre logs con la opcion 4.
if not "%pause_already_done%"=="1" pause
exit /b 0

:end
echo Saliendo del menu de validacion.
exit /b %script_exit_code%
