@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import fastapi,uvicorn" >nul 2>&1
  if not errorlevel 1 (
    ".venv\Scripts\python.exe" -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
    exit /b
  )
)
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
if errorlevel 1 (
  echo.
  echo See README.md for setup instructions. Port 8000 may already be in use.
  pause
)
