@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv was not found. Complete the setup steps in README first.
  exit /b 1
)
if not exist ".env" (
  echo ERROR: .env was not found. Copy .env.example and set your credentials.
  exit /b 1
)
if not exist "config.json" (
  echo ERROR: config.json was not found. Copy and edit config.example.json.
  exit /b 1
)

".venv\Scripts\python.exe" -m app.desktop
endlocal
