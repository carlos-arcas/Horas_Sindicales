@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\.."

set "LAST_INSTALLER_FILE=scripts\release\.last_installer_path.txt"
if exist "%LAST_INSTALLER_FILE%" del /q "%LAST_INSTALLER_FILE%" >nul 2>&1

echo [INFO] Iniciando pipeline de release Windows...

call "scripts\release\00_check_prereqs.bat"
if errorlevel 1 (
    echo [ERROR] Pipeline detenido en 00_check_prereqs.bat.
    exit /b 1
)

call "scripts\release\10_setup_venv.bat"
if errorlevel 1 (
    echo [ERROR] Pipeline detenido en 10_setup_venv.bat.
    exit /b 1
)

call "scripts\release\20_build_dist.bat"
if errorlevel 1 (
    echo [ERROR] Pipeline detenido en 20_build_dist.bat.
    exit /b 1
)

call "scripts\release\30_build_installer.bat"
if errorlevel 1 (
    echo [ERROR] Pipeline detenido en 30_build_installer.bat.
    exit /b 1
)

set "SETUP_PATH="
if exist "%LAST_INSTALLER_FILE%" (
    set /p SETUP_PATH=<"%LAST_INSTALLER_FILE%"
)

echo.
echo ==============================
echo RELEASE OK
if defined SETUP_PATH (
    echo Instalador: !SETUP_PATH!
) else (
    echo Instalador: ^(ruta no detectada automaticamente, revisar salida anterior^)
)
echo ==============================

exit /b 0
