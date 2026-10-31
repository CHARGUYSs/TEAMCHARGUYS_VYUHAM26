@echo off
setlocal
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Backend not installed. Double-click SETUP_WINDOWS.cmd first.
  pause
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo Frontend not installed. Double-click SETUP_WINDOWS.cmd first.
  pause
  exit /b 1
)
start "ReMind AI - API" "%~dp0backend\start_api.cmd"
start "ReMind AI - Web" "%~dp0frontend\start_web.cmd"
timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:5173"
echo ReMind AI launched. Keep both server windows open while demonstrating.
