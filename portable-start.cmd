@echo off
setlocal
cd /d "%~dp0"

if not exist "SwitchBotLocalLauncher.exe" (
  echo ERROR: SwitchBotLocalLauncher.exe was not found in this folder.
  echo Keep this file in the SwitchBotLocalLauncher portable folder.
  pause
  exit /b 1
)

if not exist ".env" (
  echo ERROR: .env was not found in this portable folder.
  echo Copy .env.example to .env and set your SwitchBot credentials.
  pause
  exit /b 1
)

if not exist "config.json" (
  echo ERROR: config.json was not found in this portable folder.
  echo Copy config.example.json to config.json or create a package with --with-local-config.
  pause
  exit /b 1
)

set "SWITCHBOT_PORTABLE_DATA_ROOT=%~dp0"
start "" "%~dp0SwitchBotLocalLauncher.exe"
endlocal
