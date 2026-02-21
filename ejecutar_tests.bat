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

set "RUN_SUMMARY_FILE="
if defined RUN_DIR (
    set "RUN_SUMMARY_FILE=%RUN_DIR%\summary.txt"
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

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
set "TESTS_DIR=tests"
set "COV_SRC=app"
set "HTML_DIR=%COVERAGE_HTML_DIR%"

rem contrato historico: pytest --cov=app --cov-report=term-missing --cov-fail-under=85
set "PYTEST_CMD=""%PY%"" -m pytest -q ""%TESTS_DIR%"" --cov=%COV_SRC% --cov-report=term-missing ""--cov-report=html:%HTML_DIR%"""
call :log_debug "Comando pytest: %PYTEST_CMD%"
if defined RUN_SUMMARY_FILE (
    >>"%RUN_SUMMARY_FILE%" echo CMD_PYTEST=%PYTEST_CMD%
)

>>"%LOG_PYTEST%" echo ==== pytest output ====
>>"%LOG_PYTEST%" echo Fecha: %DATE% %TIME%
call "%PY%" -m pytest -q "%TESTS_DIR%" --cov=%COV_SRC% --cov-report=term-missing "--cov-report=html:%HTML_DIR%" 1>>"%LOG_PYTEST%" 2>>"%LOG_STDERR%"
set "TEST_EXIT=%ERRORLEVEL%"

if "%TEST_EXIT%"=="0" (
    >>"%LOG_COVERAGE%" echo [OK] pytest finalizo correctamente.
) else (
    >>"%LOG_COVERAGE%" echo [WARN] pytest devolvio exit code %TEST_EXIT%.
)

python -m coverage report -m > "%LOG_COVERAGE%" 2>&1
if errorlevel 1 (
    >>"%LOG_COVERAGE%" echo [INFO] No fue posible generar coverage report detallado.
)
if exist ".coverage" (
    echo ==== coverage report -m ====
    python -m coverage report -m
)

if exist "%COVERAGE_HTML_DIR%\index.html" (
    >>"%LOG_COVERAGE%" echo [OK] Coverage HTML generado en "%COVERAGE_HTML_DIR%\index.html".
) else (
    >>"%LOG_COVERAGE%" echo [WARN] No se genero el HTML de coverage en "%COVERAGE_HTML_DIR%".
)

if defined RUN_SUMMARY_FILE (
    >>"%RUN_SUMMARY_FILE%" echo PYTEST_EXIT_CODE=%TEST_EXIT%
    >>"%RUN_SUMMARY_FILE%" echo TESTS_STDOUT_LOG=%LOG_PYTEST%
    >>"%RUN_SUMMARY_FILE%" echo TESTS_STDERR_LOG=%LOG_STDERR%
)

call :log_debug "Exit code pytest: %TEST_EXIT%"
exit /b %TEST_EXIT%

:log_debug
echo [%date% %time%] %~1>> "%LOG_DEBUG%"
exit /b 0
