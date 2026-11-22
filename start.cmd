@echo off
setlocal
if not exist "%~dp0data" mkdir "%~dp0data"
where py >nul 2>nul
if errorlevel 1 (
  set "PY=python"
) else (
  set "PY=py"
)
%PY% "%~dp0generate_inventory.py" %* > "%~dp0data\last_run.log" 2>&1
type "%~dp0data\last_run.log"
if errorlevel 1 pause
endlocal
