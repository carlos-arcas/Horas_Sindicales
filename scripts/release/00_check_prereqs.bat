@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\.."

echo [INFO] Verificando prerequisitos para release Windows...

where py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se encontro el launcher de Python ^("py"^).
    echo         Instala Python 3 para Windows desde https://www.python.org/downloads/windows/
    echo         y marca la opcion de agregar Python al PATH.
    exit /b 1
)

py -V >nul 2>&1
if errorlevel 1 (
    echo [ERROR] El comando "py -V" fallo.
    echo         Revisa la instalacion de Python y vuelve a intentarlo.
    exit /b 1
)

if not exist "packaging\HorasSindicales.spec" (
    echo [ERROR] No existe packaging\HorasSindicales.spec.
    echo         Crea o copia el archivo .spec en esa ruta antes de compilar.
    exit /b 1
)

if not exist "installer\HorasSindicales.iss" (
    echo [ERROR] No existe installer\HorasSindicales.iss.
    echo         Crea o copia el script de Inno Setup en esa ruta antes de compilar.
    exit /b 1
)

set "ISCC_PATH="
where ISCC.exe >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%I in ('where ISCC.exe') do (
        set "ISCC_PATH=%%~fI"
        goto :iscc_found
    )
)

if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    goto :iscc_found
)

if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
    goto :iscc_found
)

echo [ERROR] No se encontro ISCC.exe ^(Inno Setup Compiler^).
echo         Instala Inno Setup 6 y agrega ISCC al PATH,
echo         o verifica estas rutas:
echo           - C:\Program Files ^(x86^)\Inno Setup 6\ISCC.exe
echo           - C:\Program Files\Inno Setup 6\ISCC.exe
exit /b 1

:iscc_found
echo [INFO] ISCC encontrado en: !ISCC_PATH!

echo [OK] Prerequisitos verificados correctamente.
exit /b 0
