@echo off
setlocal
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Run SETUP_WINDOWS.cmd first.
  pause
  exit /b 1
)
"backend\.venv\Scripts\python.exe" "backend\scripts\verify_setup.py"
echo.
echo Check the details above. Troubleshooting is in README.md.
pause
