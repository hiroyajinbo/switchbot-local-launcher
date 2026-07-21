# Portable Package

This package is for running SwitchBot Local Launcher on another Windows PC without a
Python development setup.

## Start

Run:

```cmd
start.cmd
```

The portable `start.cmd` keeps settings in this folder:

```text
SwitchBotLocalLauncher-portable\.env
SwitchBotLocalLauncher-portable\config.json
SwitchBotLocalLauncher-portable\logs
```

This is different from running `SwitchBotLocalLauncher.exe` directly. Direct EXE
startup uses the normal desktop app data folder:

```text
%LOCALAPPDATA%\SwitchBotLocalLauncher
```

## First Setup On Another PC

If this package only contains templates:

1. Copy `.env.example` to `.env`.
2. Set `SWITCHBOT_TOKEN` and `SWITCHBOT_SECRET` in `.env`.
3. Copy `config.example.json` to `config.json`.
4. Edit `config.json` or use the app edit mode after startup.
5. Run `start.cmd`.

`start.cmd` stops before launch when `.env` or `config.json` is missing, so the
portable package does not silently fall back to the normal app-data settings.

If the package was created with `--with-local-config`, `.env` and `config.json` are
already included. Keep that package private because `.env` contains credentials.

## Create A Package

From the development project folder:

```cmd
package-portable.cmd
```

This creates:

```text
dist\portable\SwitchBotLocalLauncher-portable
dist\portable\SwitchBotLocalLauncher-portable.zip
```

To include the current local `.env` and `config.json`:

```cmd
package-portable.cmd --with-local-config
```

To rebuild from a clean PyInstaller cache:

```cmd
package-portable.cmd --clean
```
