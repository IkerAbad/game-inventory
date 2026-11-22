@echo off
setlocal
if not exist "%~dp0data" mkdir "%~dp0data"
py "%~dp0generate_inventory.py" %* > "%~dp0data\last_run.log" 2>&1
type "%~dp0data\last_run.log"
if errorlevel 1 pause
endlocal
