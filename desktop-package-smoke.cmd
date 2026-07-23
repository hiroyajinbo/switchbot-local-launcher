@echo off
setlocal
cd /d "%~dp0"

call build-desktop.cmd
if errorlevel 1 exit /b %errorlevel%

call desktop-smoke.cmd --executable dist\SwitchBotLocalLauncher\SwitchBotLocalLauncher.exe
exit /b %errorlevel%
