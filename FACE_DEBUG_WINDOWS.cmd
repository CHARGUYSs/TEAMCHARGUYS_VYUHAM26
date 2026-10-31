@echo off
setlocal
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Please run SETUP_WINDOWS.cmd first.
  pause
  exit /b 1
)
if "%~1"=="" (
  echo Drag a portrait JPG or PNG onto this FACE_DEBUG_WINDOWS.cmd file.
  echo OR run it in CMD like:
  echo FACE_DEBUG_WINDOWS.cmd "C:\Photos\portrait.jpg"
  pause
  exit /b 1
)
"backend\.venv\Scripts\python.exe" "backend\scripts\face_debug.py" %*
pause
