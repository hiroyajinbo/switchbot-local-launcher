@echo off
setlocal
cd /d "%~dp0"

set "INCLUDE_LOCAL_CONFIG="
set "CLEAN_OPTION="

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--with-local-config" (
  set "INCLUDE_LOCAL_CONFIG=1"
  shift
  goto parse_args
)
if /i "%~1"=="--clean" (
  set "CLEAN_OPTION=--clean"
  shift
  goto parse_args
)
echo ERROR: Unknown option: %~1
echo Usage: package-portable.cmd [--clean] [--with-local-config]
exit /b 1

:args_done
call build-desktop.cmd %CLEAN_OPTION%
if errorlevel 1 exit /b %errorlevel%

set "SOURCE_DIR=dist\SwitchBotLocalLauncher"
set "PACKAGE_ROOT=dist\portable"
set "PACKAGE_DIR=%PACKAGE_ROOT%\SwitchBotLocalLauncher-portable"
set "ZIP_PATH=%PACKAGE_ROOT%\SwitchBotLocalLauncher-portable.zip"

if not exist "%SOURCE_DIR%\SwitchBotLocalLauncher.exe" (
  echo ERROR: Built executable was not found: %SOURCE_DIR%\SwitchBotLocalLauncher.exe
  exit /b 1
)

if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
if errorlevel 1 exit /b %errorlevel%
mkdir "%PACKAGE_DIR%"
if errorlevel 1 exit /b %errorlevel%

xcopy "%SOURCE_DIR%\*" "%PACKAGE_DIR%\" /E /I /Y >nul
if errorlevel 1 exit /b %errorlevel%

copy /Y "portable-start.cmd" "%PACKAGE_DIR%\start.cmd" >nul
if errorlevel 1 exit /b %errorlevel%
copy /Y ".env.example" "%PACKAGE_DIR%\.env.example" >nul
if errorlevel 1 exit /b %errorlevel%
copy /Y "config.example.json" "%PACKAGE_DIR%\config.example.json" >nul
if errorlevel 1 exit /b %errorlevel%
copy /Y "docs\portable-package.md" "%PACKAGE_DIR%\README_PORTABLE.md" >nul
if errorlevel 1 exit /b %errorlevel%

if defined INCLUDE_LOCAL_CONFIG (
  if not exist ".env" (
    echo ERROR: --with-local-config was specified, but .env was not found.
    exit /b 1
  )
  if not exist "config.json" (
    echo ERROR: --with-local-config was specified, but config.json was not found.
    exit /b 1
  )
  copy /Y ".env" "%PACKAGE_DIR%\.env" >nul
  if errorlevel 1 exit /b %errorlevel%
  copy /Y "config.json" "%PACKAGE_DIR%\config.json" >nul
  if errorlevel 1 exit /b %errorlevel%
)

if exist "%ZIP_PATH%" del /q "%ZIP_PATH%"
if errorlevel 1 exit /b %errorlevel%

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%PACKAGE_DIR%\*' -DestinationPath '%ZIP_PATH%' -Force"
if errorlevel 1 exit /b %errorlevel%

echo.
echo Portable package complete:
echo   Folder: %PACKAGE_DIR%
echo   Zip:    %ZIP_PATH%
if defined INCLUDE_LOCAL_CONFIG (
  echo.
  echo WARNING: This package includes .env and config.json.
  echo Keep it private because it contains SwitchBot credentials.
) else (
  echo.
  echo NOTE: This package includes templates only.
  echo Copy .env.example to .env and config.example.json to config.json on the target PC.
)
endlocal
