@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo    ReMind AI - Windows setup
 echo ========================================
where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher missing. Install Python 3.10 or newer from python.org.
  pause
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo Node.js/npm missing. Install Node.js 20 LTS, then retry.
  pause
  exit /b 1
)
echo.
echo [1/4] Creating isolated Python environment...
py -3 -m venv "backend\.venv"
if errorlevel 1 goto failed
"backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 goto failed
echo.
echo [2/4] Installing web app dependencies...
cd /d "%~dp0frontend"
call npm ci
if errorlevel 1 goto failed
cd /d "%~dp0"
echo.
echo [3/4] Installing verified face recognition models (~39 MB)...
"%~dp0backend\.venv\Scripts\python.exe" "%~dp0backend\scripts\download_models.py"
if errorlevel 1 (
  echo.
  echo WARNING: AI model download was blocked. The site will work, but cannot name faces yet.
  echo Retry later with MODEL_SETUP_WINDOWS.cmd or the Install AI models button.
)
echo.
echo [4/4] Setup complete. Launch START_WINDOWS.cmd now.
echo.
pause
exit /b 0
:failed
echo.
echo Setup failed. Review the error above and read README.md.
pause
exit /b 1
