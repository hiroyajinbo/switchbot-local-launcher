@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv was not found. Complete the setup steps in README first.
  exit /b 1
)

set "CLEAN_OPTION="
if /i "%~1"=="--clean" set "CLEAN_OPTION=--clean"

".venv\Scripts\python.exe" -m PyInstaller --noconfirm %CLEAN_OPTION% switchbot-local-launcher.spec
if errorlevel 1 exit /b %errorlevel%

echo.
echo Build complete: dist\SwitchBotLocalLauncher\SwitchBotLocalLauncher.exe
endlocal
