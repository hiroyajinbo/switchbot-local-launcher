@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv was not found. Complete the setup steps in README first.
  exit /b 1
)

".venv\Scripts\python.exe" scripts\desktop_smoke_test.py %*
exit /b %errorlevel%
