@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 (
  echo Could not start the API. Review the error above.
  pause
)
