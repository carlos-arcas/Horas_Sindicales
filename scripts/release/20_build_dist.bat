@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\.."

echo [INFO] Compilando distribucion con PyInstaller...

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo [ERROR] No se encontro .venv\Scripts\pyinstaller.exe.
    echo         Ejecuta primero scripts\release\10_setup_venv.bat.
    exit /b 1
)

if not exist "packaging\HorasSindicales.spec" (
    echo [ERROR] No existe packaging\HorasSindicales.spec.
    echo         Ejecuta scripts\release\00_check_prereqs.bat para diagnosticar.
    exit /b 1
)

if exist "build" (
    echo [INFO] Eliminando build\ anterior...
    rmdir /s /q "build"
    if exist "build" (
        echo [ERROR] No se pudo eliminar build\.
        exit /b 1
    )
)

if exist "dist" (
    echo [INFO] Eliminando dist\ anterior...
    rmdir /s /q "dist"
    if exist "dist" (
        echo [ERROR] No se pudo eliminar dist\.
        exit /b 1
    )
)

echo [INFO] Ejecutando PyInstaller con el archivo .spec...
".venv\Scripts\pyinstaller.exe" --noconfirm --clean "packaging\HorasSindicales.spec"
if errorlevel 1 (
    echo [ERROR] PyInstaller fallo al compilar.
    exit /b 1
)

if exist "dist\HorasSindicales\" (
    echo [OK] Distribucion generada en dist\HorasSindicales\
    exit /b 0
)

set "DIST_FOLDERS="
for /d %%D in ("dist\*") do (
    set "DIST_FOLDERS=!DIST_FOLDERS! %%~nxD"
)

if defined DIST_FOLDERS (
    echo [WARN] No existe dist\HorasSindicales\ pero se detectaron carpetas en dist\:!DIST_FOLDERS!
    echo [OK] Revisar nombre de salida configurado en packaging\HorasSindicales.spec.
    exit /b 0
)

echo [ERROR] No se detecto ninguna salida en dist\ tras ejecutar PyInstaller.
exit /b 1
