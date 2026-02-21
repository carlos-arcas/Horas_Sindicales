@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "LOG_DIR=%ROOT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "LOG_STDOUT=%LOG_DIR%\tests_stdout.log"
set "LOG_STDERR=%LOG_DIR%\tests_stderr.log"
set "LOG_DEBUG=%LOG_DIR%\tests_debug.log"
set "LOG_PYTEST=%LOG_DIR%\pytest_output.txt"
set "LOG_COVERAGE=%LOG_DIR%\coverage_report.txt"
set "COVERAGE_SUMMARY=%LOG_DIR%\coverage_summary.txt"
set "COVERAGE_JSON=%LOG_DIR%\coverage.json"

set "RUN_SUMMARY_FILE=%LOG_DIR%\summary.txt"
if defined RUN_DIR set "RUN_SUMMARY_FILE=%RUN_DIR%\summary.txt"
if defined RUN_DIR (
    set "LOG_STDOUT=%RUN_DIR%\tests_stdout.txt"
    set "LOG_STDERR=%RUN_DIR%\tests_stderr.txt"
    set "COVERAGE_SUMMARY=%RUN_DIR%\coverage_summary.txt"
    set "COVERAGE_JSON=%RUN_DIR%\coverage.json"
)

>"%LOG_PYTEST%" echo ==== pytest output ====
>>"%LOG_PYTEST%" echo Fecha: %DATE% %TIME%
>"%LOG_COVERAGE%" echo ==== coverage report ====
>>"%LOG_COVERAGE%" echo Fecha: %DATE% %TIME%

call :log_debug "==== ejecutar_tests.bat ===="
call :log_debug "Repositorio: %ROOT_DIR%"

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
    echo [ERROR] No se encontro Python (^".venv\Scripts\python.exe^", ^"py -3^" ni ^"python^"^).
    >>"%LOG_PYTEST%" echo [ERROR] No se encontro Python para ejecutar pytest.
    >>"%LOG_COVERAGE%" echo [ERROR] Sin Python: no se puede calcular cobertura.
    call :log_debug "ERROR: No se encontro Python"
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    call :log_debug "Creando .venv"
    %PYTHON_CMD% -m venv .venv >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
    if errorlevel 1 (
        echo [ERROR] Fallo al crear .venv. Revisa logs.
        >>"%LOG_PYTEST%" echo [ERROR] Fallo al crear .venv.
        >>"%LOG_COVERAGE%" echo [ERROR] Fallo al crear .venv.
        call :log_debug "ERROR: Fallo creando .venv"
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat" >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    echo [ERROR] No se pudo activar .venv.
    >>"%LOG_PYTEST%" echo [ERROR] No se pudo activar .venv.
    >>"%LOG_COVERAGE%" echo [ERROR] No se pudo activar .venv.
    call :log_debug "ERROR: Fallo activando .venv"
    exit /b 1
)

call :log_debug "Python activo:"
python --version >> "%LOG_DEBUG%" 2>&1

python -m pip install --upgrade pip >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    echo [ERROR] Fallo al actualizar pip. Revisa logs.
    >>"%LOG_PYTEST%" echo [ERROR] Fallo al actualizar pip.
    >>"%LOG_COVERAGE%" echo [ERROR] Fallo al actualizar pip.
    call :log_debug "ERROR: pip upgrade fallo"
    exit /b 1
)

python -m pip install -r requirements.txt >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 1 (
    echo [ERROR] Fallo al instalar requirements.txt. Revisa logs.
    >>"%LOG_PYTEST%" echo [ERROR] Fallo al instalar requirements.txt.
    >>"%LOG_COVERAGE%" echo [ERROR] Fallo al instalar requirements.txt.
    call :log_debug "ERROR: pip install requirements.txt fallo"
    exit /b 1
)

if exist "requirements-dev.txt" (
    python -m pip install -r requirements-dev.txt >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
    if errorlevel 1 (
        echo [ERROR] Fallo al instalar requirements-dev.txt. Revisa logs.
        >>"%LOG_PYTEST%" echo [ERROR] Fallo al instalar requirements-dev.txt.
        >>"%LOG_COVERAGE%" echo [ERROR] Fallo al instalar requirements-dev.txt.
        call :log_debug "ERROR: pip install requirements-dev.txt fallo"
        exit /b 1
    )
) else (
    echo [ERROR] Falta requirements-dev.txt para ejecutar tests.
    >>"%LOG_PYTEST%" echo [ERROR] Falta requirements-dev.txt para ejecutar tests.
    >>"%LOG_COVERAGE%" echo [ERROR] Falta requirements-dev.txt para ejecutar tests.
    call :log_debug "ERROR: No existe requirements-dev.txt"
    exit /b 1
)

python scripts/preflight_tests.py >> "%LOG_STDOUT%" 2>> "%LOG_STDERR%"
if errorlevel 3 (
    echo [ERROR] Preflight de tests fallo por error interno. Revisa logs.
    >>"%LOG_PYTEST%" echo [ERROR] Preflight de tests fallo por error interno.
    >>"%LOG_COVERAGE%" echo [ERROR] Preflight de tests fallo por error interno.
    call :log_debug "ERROR: preflight_tests.py error interno"
    exit /b 3
)
if errorlevel 2 (
    echo [ERROR] Preflight de tests: faltan dependencias obligatorias (^"pytest-cov^" y/o ^"pytest^"^). Revisa logs.
    >>"%LOG_PYTEST%" echo [ERROR] Faltan dependencias obligatorias para pytest.
    >>"%LOG_COVERAGE%" echo [ERROR] Faltan dependencias obligatorias para cobertura.
    call :log_debug "ERROR: preflight_tests.py dependencias faltantes"
    exit /b 2
)
if errorlevel 1 (
    echo [ERROR] Preflight de tests fallo.
    >>"%LOG_PYTEST%" echo [ERROR] Preflight de tests fallo.
    >>"%LOG_COVERAGE%" echo [ERROR] Preflight de tests fallo.
    call :log_debug "ERROR: preflight_tests.py fallo inesperado"
    exit /b 1
)

set "COVERAGE_HTML_DIR=%LOG_DIR%\coverage_html"
if defined RUN_DIR set "COVERAGE_HTML_DIR=%RUN_DIR%\coverage_html"

if not exist "%COVERAGE_HTML_DIR%" mkdir "%COVERAGE_HTML_DIR%" >nul 2>&1

rem contrato: pytest --cov=app --cov-report=term-missing (sin gate de umbral en este paso)
set "PYTEST_CMD=python -m pytest -q tests --cov=app --cov-report=term-missing --cov-report=html:\"%COVERAGE_HTML_DIR%\""
call :log_debug "Comando pytest: %PYTEST_CMD%"
if defined RUN_SUMMARY_FILE (
    >>"%RUN_SUMMARY_FILE%" echo CMD_PYTEST=%PYTEST_CMD%
)

echo [INFO] Ejecutando: %PYTEST_CMD%
>>"%LOG_PYTEST%" echo [INFO] CMD: %PYTEST_CMD%
python -m pytest -q tests --cov=app --cov-report=term-missing --cov-report=html:"%COVERAGE_HTML_DIR%" 1>>"%LOG_STDOUT%" 2>>"%LOG_STDERR%"
set "TEST_EXIT=%ERRORLEVEL%"
set "FINAL_REASON=pytest devolvio exit code %TEST_EXIT%"
if "%TEST_EXIT%"=="0" set "FINAL_REASON=pytest ok"

findstr /i /c:"collected 0 items" "%LOG_STDOUT%" >nul 2>&1
if not errorlevel 1 (
    echo [ERROR] Pytest no encontro tests. Causa tipica: ruta mal entrecomillada o ejecucion desde directorio incorrecto. Ejecuta opcion 1 desde el menu o corre: pytest -q tests
    >>"%LOG_PYTEST%" echo [ERROR] Pytest no encontro tests. Causa tipica: ruta mal entrecomillada o ejecucion desde directorio incorrecto. Ejecuta opcion 1 desde el menu o corre: pytest -q tests
    if defined RUN_SUMMARY_FILE (
        >>"%RUN_SUMMARY_FILE%" echo ERROR_HUMANO=Pytest no encontro tests. Causa tipica: ruta mal entrecomillada o ejecucion desde directorio incorrecto.
    )
)

if "%TEST_EXIT%"=="0" (
    >>"%LOG_COVERAGE%" echo [OK] pytest finalizo correctamente.
) else (
    >>"%LOG_COVERAGE%" echo [WARN] pytest devolvio exit code %TEST_EXIT%.
)
python -m coverage report -m > "%LOG_COVERAGE%" 2>&1
if errorlevel 1 (
    >>"%LOG_COVERAGE%" echo [INFO] No fue posible generar coverage report detallado.
)
set "COVERAGE_TOTAL=N/D"
for /f "tokens=4" %%P in ('findstr /r /c:"^TOTAL[ ]" "%LOG_COVERAGE%"') do set "COVERAGE_TOTAL=%%P"
if exist ".coverage" (
    echo ==== coverage report -m ====
    python -m coverage report -m
    python scripts/coverage_summary.py --package app --threshold 85 --out-txt "%COVERAGE_SUMMARY%" --out-json "%COVERAGE_JSON%" 1>>"%LOG_STDOUT%" 2>>"%LOG_STDERR%"
    if errorlevel 1 (
        >>"%LOG_COVERAGE%" echo [WARN] No fue posible generar coverage_summary.txt.
    ) else (
        >>"%LOG_COVERAGE%" echo [OK] Coverage summary generado en "%COVERAGE_SUMMARY%".
    )
)

if exist "%COVERAGE_HTML_DIR%\index.html" (
    >>"%LOG_COVERAGE%" echo [OK] Coverage HTML generado en "%COVERAGE_HTML_DIR%\index.html".
) else (
    echo [ERROR] No se genero el HTML de coverage. Motivos comunes: pytest fallo, no se ejecutaron tests, o falta pytest-cov. Revisa logs: "%LOG_PYTEST%"
    >>"%LOG_COVERAGE%" echo [ERROR] No se genero el HTML de coverage. Motivos comunes: pytest fallo, no se ejecutaron tests, o falta pytest-cov. Revisa logs: "%LOG_PYTEST%"
    if defined RUN_SUMMARY_FILE (
        >>"%RUN_SUMMARY_FILE%" echo ERROR_HUMANO=No se genero el HTML de coverage. Motivos comunes: pytest fallo, no se ejecutaron tests, o falta pytest-cov.
    )
)

call :log_debug "Exit code pytest: %TEST_EXIT%"
if "%TEST_EXIT%"=="0" (
    set "PYTEST_RESULT=PASS"
) else (
    set "PYTEST_RESULT=FAIL"
)
set "EXIT_REASON=%FINAL_REASON%"
>"%RUN_SUMMARY_FILE%" echo ==== ejecutar_tests summary ====
>>"%RUN_SUMMARY_FILE%" echo Fecha: %DATE% %TIME%
>>"%RUN_SUMMARY_FILE%" echo Command=%PYTEST_CMD%
>>"%RUN_SUMMARY_FILE%" echo Pytest=%PYTEST_RESULT%
>>"%RUN_SUMMARY_FILE%" echo Coverage_TOTAL=%COVERAGE_TOTAL%
>>"%RUN_SUMMARY_FILE%" echo tests_exit_code=%TEST_EXIT%
>>"%RUN_SUMMARY_FILE%" echo coverage_percent=%COVERAGE_TOTAL%
>>"%RUN_SUMMARY_FILE%" echo gate_exit_code=N/A
>>"%RUN_SUMMARY_FILE%" echo ExitCode=%TEST_EXIT%
>>"%RUN_SUMMARY_FILE%" echo ExitReason=%EXIT_REASON%
exit /b %TEST_EXIT%

:log_debug
echo [%date% %time%] %~1>> "%LOG_DEBUG%"
exit /b 0
