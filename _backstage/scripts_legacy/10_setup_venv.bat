@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\.."

echo [INFO] Preparando entorno virtual...

where py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se encontro el comando "py".
    echo         Ejecuta primero scripts\release\00_check_prereqs.bat.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creando .venv...
    py -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual .venv.
        exit /b 1
    )
) else (
    echo [INFO] .venv ya existe. Se reutilizara.
)

echo [INFO] Actualizando pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Fallo la actualizacion de pip.
    exit /b 1
)

if exist "requirements-dev.txt" (
    echo [INFO] Instalando dependencias desde requirements-dev.txt...
    ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion de requirements-dev.txt.
        exit /b 1
    )
) else (
    if not exist "requirements.txt" (
        echo [ERROR] No existe requirements.txt ni requirements-dev.txt.
        echo         Crea al menos uno de esos archivos para continuar.
        exit /b 1
    )

    echo [INFO] Instalando dependencias desde requirements.txt...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion de requirements.txt.
        exit /b 1
    )

    echo [INFO] Instalando pyinstaller...
    ".venv\Scripts\python.exe" -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion de pyinstaller.
        exit /b 1
    )
)

echo [OK] Entorno virtual listo.
exit /b 0
