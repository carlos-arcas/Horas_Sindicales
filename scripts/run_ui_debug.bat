@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

if not exist "logs" mkdir "logs"

del /q "logs\stdout.log" "logs\stderr.log" "logs\exit_code.txt" >nul 2>nul

set "PYTHONFAULTHANDLER=1"
set "QT_LOGGING_RULES=qt.*=true"

python -X faulthandler -m app.entrypoints.ui_main > "logs\stdout.log" 2> "logs\stderr.log"
set "APP_EXIT_CODE=%ERRORLEVEL%"

echo %APP_EXIT_CODE%> "logs\exit_code.txt"

if not exist "logs\boot_trace.log" exit /b 1

findstr /c:"Cannot create children" "logs\stderr.log" >nul
if %ERRORLEVEL%==0 exit /b 2

exit /b %APP_EXIT_CODE%
