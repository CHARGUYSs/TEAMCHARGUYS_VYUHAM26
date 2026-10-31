@echo off
setlocal
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Run SETUP_WINDOWS.cmd first.
  pause
  exit /b 1
)
"backend\.venv\Scripts\python.exe" "backend\scripts\download_models.py"
if errorlevel 1 (
  echo Download failed. Check connection or follow manual download steps in README.md.
) else (
  echo Models verified. Restart the API if it was already running, then refresh the browser.
)
pause
