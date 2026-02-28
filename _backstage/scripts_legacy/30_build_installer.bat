@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\.."

set "LAST_INSTALLER_FILE=scripts\release\.last_installer_path.txt"
if exist "%LAST_INSTALLER_FILE%" del /q "%LAST_INSTALLER_FILE%" >nul 2>&1

echo [INFO] Compilando instalador con Inno Setup...

if not exist "dist\" (
    echo [ERROR] No existe la carpeta dist\.
    echo         Ejecuta antes scripts\release\20_build_dist.bat.
    exit /b 1
)

if not exist "installer\HorasSindicales.iss" (
    echo [ERROR] No existe installer\HorasSindicales.iss.
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

echo [ERROR] No se encontro ISCC.exe.
echo         Ejecuta scripts\release\00_check_prereqs.bat para mas detalles.
exit /b 1

:iscc_found
echo [INFO] Usando ISCC: !ISCC_PATH!

"!ISCC_PATH!" "installer\HorasSindicales.iss"
set "ISCC_EXIT=%ERRORLEVEL%"

rem Codigos de salida ISCC:
rem 0 = compilacion correcta
rem 1 = parametros invalidos o error interno
rem 2 = compilacion fallida
if "%ISCC_EXIT%"=="0" (
    echo [INFO] ISCC finalizo correctamente.
) else if "%ISCC_EXIT%"=="1" (
    echo [ERROR] ISCC devolvio codigo 1: parametros invalidos o error interno.
    exit /b 1
) else if "%ISCC_EXIT%"=="2" (
    echo [ERROR] ISCC devolvio codigo 2: fallo de compilacion del instalador.
    exit /b 1
) else (
    echo [ERROR] ISCC devolvio codigo inesperado: %ISCC_EXIT%
    exit /b 1
)

set "SETUP_EXE="
for /f "delims=" %%F in ('dir /b /a:-d /o:-d "output\*.exe" 2^>nul') do (
    set "SETUP_EXE=%CD%\output\%%F"
    goto :setup_found
)

for /f "delims=" %%F in ('dir /b /a:-d /o:-d "installer\output\*.exe" 2^>nul') do (
    set "SETUP_EXE=%CD%\installer\output\%%F"
    goto :setup_found
)

if exist "installer\HorasSindicalesSetup.exe" (
    set "SETUP_EXE=%CD%\installer\HorasSindicalesSetup.exe"
    goto :setup_found
)

if exist "HorasSindicalesSetup.exe" (
    set "SETUP_EXE=%CD%\HorasSindicalesSetup.exe"
    goto :setup_found
)

echo [ERROR] No se encontro el .exe final del instalador.
echo         Revisa OutputDir y OutputBaseFilename en installer\HorasSindicales.iss.
exit /b 1

:setup_found
echo [OK] Instalador generado en:
echo       !SETUP_EXE!
>"%LAST_INSTALLER_FILE%" echo !SETUP_EXE!

exit /b 0
