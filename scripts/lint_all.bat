@echo off
setlocal

set "ROOT=%~dp0.."
set "VENV_DIR=%ROOT%\.venv"

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [lint_all] Creando entorno virtual en %VENV_DIR%...
    py -3 -m venv "%VENV_DIR%"
    if errorlevel 1 goto :error
)

echo [lint_all] Activando entorno virtual...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 goto :error

echo [lint_all] Instalando dependencias...
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r "%ROOT%\requirements-dev.txt"
if errorlevel 1 goto :error

echo [lint_all] Ejecutando lint_all.py...
python "%ROOT%\scripts\lint_all.py"
if errorlevel 1 goto :error

echo [lint_all] Finalizado correctamente.
exit /b 0

:error
echo [lint_all] Fallo durante la ejecucion.
exit /b 1
