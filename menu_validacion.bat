@echo off
setlocal EnableExtensions
set "ROOT_DIR=%~dp0"
call "%ROOT_DIR%scripts\menu_validacion.bat"
exit /b %ERRORLEVEL%
