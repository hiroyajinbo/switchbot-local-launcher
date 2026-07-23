@echo off
setlocal
cd /d "%~dp0"

if not exist "SwitchBotLocalLauncher.exe" (
  echo ERROR: SwitchBotLocalLauncher.exe was not found in this folder.
  echo Keep this file in the SwitchBotLocalLauncher portable folder.
  pause
  exit /b 1
)

if not exist "config.json" (
  if not exist "config.example.json" (
    echo ERROR: config.json and config.example.json were not found in this portable folder.
    pause
    exit /b 1
  )
  copy /Y "config.example.json" "config.json" >nul
  if errorlevel 1 exit /b %errorlevel%
)

set "SWITCHBOT_PORTABLE_DATA_ROOT=%~dp0"
start "" "%~dp0SwitchBotLocalLauncher.exe"
endlocal
