@echo off
setlocal
if not exist "%~dp0datos" mkdir "%~dp0datos"
py "%~dp0generar_inventario.py" %* > "%~dp0datos\ultima_ejecucion.log" 2>&1
type "%~dp0datos\ultima_ejecucion.log"
if errorlevel 1 pause
endlocal
