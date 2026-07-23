@echo off
setlocal
cd /d "%~dp0"

set "DIRTY="
for /f "delims=" %%I in ('git status --porcelain') do set "DIRTY=1"
if defined DIRTY (
  echo ERROR: Local changes were found. Commit or stash them before updating.
  git status --short
  pause
  exit /b 1
)

echo Updating the current branch...
git pull --ff-only
if errorlevel 1 (
  echo ERROR: Git update failed. The application was not started.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv was not found. Complete the setup steps in README first.
  pause
  exit /b 1
)

echo Synchronizing Python dependencies...
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (
  echo ERROR: Dependency installation failed. The application was not started.
  pause
  exit /b 1
)

echo Starting SwitchBot Local Launcher...
call start.cmd
