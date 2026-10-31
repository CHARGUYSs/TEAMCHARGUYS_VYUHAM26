@echo off
cd /d "%~dp0"
call npm run dev
if errorlevel 1 (
  echo Could not start the frontend. Review the error above.
  pause
)
