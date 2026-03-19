@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0..\"
cd /d "%ROOT_DIR%"

set "BASE_DIR=%ROOT_DIR%logs\windows_real"
if not exist "%BASE_DIR%" mkdir "%BASE_DIR%" >nul 2>&1

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "RUN_ID=%%I"
if not defined RUN_ID set "RUN_ID=%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "RUN_ID=%RUN_ID: =0%"

set "RUN_DIR=%BASE_DIR%\%RUN_ID%"
mkdir "%RUN_DIR%" >nul 2>&1

set "RESUMEN=%RUN_DIR%\resumen_validacion_windows_real.txt"
set "ENTORNO=%RUN_DIR%\entorno.txt"
set "PASOS=%RUN_DIR%\pasos_ejecutados.txt"

>"%RESUMEN%" echo ==== VALIDACION WINDOWS REAL ====
>>"%RESUMEN%" echo RunId=%RUN_ID%
>>"%RESUMEN%" echo EstadoInicial=PRODUCTO CANDIDATO A CIERRE
>>"%RESUMEN%" echo DictamenFinal=PENDIENTE
>>"%RESUMEN%" echo.
>>"%RESUMEN%" echo Completar manualmente PASS/FAIL/WARNING por paso.
>>"%RESUMEN%" echo.
>>"%RESUMEN%" echo PASO 0 ^| git rev-parse HEAD ^| PENDIENTE ^|
>>"%RESUMEN%" echo PASO 1 ^| scripts\validar_windows_real.bat ^| PASS ^| carpeta creada
>>"%RESUMEN%" echo PASO 2 ^| setup.bat ^| PENDIENTE ^|
>>"%RESUMEN%" echo PASO 3 ^| lanzar_app.bat ^| PENDIENTE ^| validar apertura UI real y cierre
>>"%RESUMEN%" echo PASO 4 ^| ejecutar_tests.bat ^| PENDIENTE ^| cobertura contractual
>>"%RESUMEN%" echo PASO 5 ^| quality_gate.bat ^| PENDIENTE ^|
>>"%RESUMEN%" echo PASO 6 ^| auditar_e2e.bat --dry-run ^| PENDIENTE ^|
>>"%RESUMEN%" echo PASO 7 ^| auditar_e2e.bat --write ^| PENDIENTE ^|
>>"%RESUMEN%" echo PASO 8 ^| launcher.bat ^| PENDIENTE ^| validar menu y rutas de logs

>"%ENTORNO%" echo ROOT_DIR=%ROOT_DIR%
>>"%ENTORNO%" echo RUN_DIR=%RUN_DIR%
>>"%ENTORNO%" echo DATE=%DATE%
>>"%ENTORNO%" echo TIME=%TIME%
>>"%ENTORNO%" echo COMPUTERNAME=%COMPUTERNAME%
>>"%ENTORNO%" echo USERNAME=%USERNAME%

>"%PASOS%" echo 1. git rev-parse HEAD
>>"%PASOS%" echo 2. py -3 --version ^|^| python --version
>>"%PASOS%" echo 3. setup.bat
>>"%PASOS%" echo 4. lanzar_app.bat
>>"%PASOS%" echo 5. ejecutar_tests.bat
>>"%PASOS%" echo 6. quality_gate.bat
>>"%PASOS%" echo 7. auditar_e2e.bat --dry-run
>>"%PASOS%" echo 8. auditar_e2e.bat --write
>>"%PASOS%" echo 9. launcher.bat

if exist ".git" (
    git rev-parse HEAD >> "%ENTORNO%" 2>&1
)
where py >nul 2>nul
if not errorlevel 1 (
    py -3 --version >> "%ENTORNO%" 2>&1
) else (
    python --version >> "%ENTORNO%" 2>&1
)

echo [OK] Carpeta de evidencia creada: %RUN_DIR%
echo [INFO] Completa la validacion siguiendo: docs\validacion_windows_real.md
echo [INFO] Resumen editable: %RESUMEN%
exit /b 0
