from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any

from app.data_paths import PORTABLE_DATA_ROOT_ENV
from app.errors import LauncherError

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "SwitchBotLocalLauncher"


class DesktopIntegration:
    def __init__(
        self,
        log_path: str | Path,
        config_path: str | Path | None = None,
        *,
        command: str | None = None,
        registry: Any | None = None,
        folder_opener: Callable[[str], Any] | None = None,
    ) -> None:
        self.log_directory = Path(log_path).resolve().parent
        self.config_path = Path(config_path).resolve() if config_path is not None else None
        self.command = command or desktop_autostart_command()
        self._registry = registry
        self._folder_opener = folder_opener or _open_folder

    def status(self) -> dict[str, Any]:
        storage_mode = "portable" if os.getenv(PORTABLE_DATA_ROOT_ENV, "").strip() else "appdata"
        available = sys.platform == "win32"
        return {
            "available": available,
            "autostart_enabled": self.autostart_enabled() if available else False,
            "storage_mode": storage_mode,
            "config_path": str(self.config_path) if self.config_path is not None else None,
            "log_directory": str(self.log_directory),
        }

    def autostart_enabled(self) -> bool:
        registry = self._registry or _winreg()
        try:
            with registry.OpenKey(
                registry.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                registry.KEY_READ,
            ) as key:
                value, _value_type = registry.QueryValueEx(key, RUN_VALUE_NAME)
        except FileNotFoundError:
            return False
        return value == self.command

    def set_autostart(self, enabled: bool) -> bool:
        registry = self._registry or _winreg()
        try:
            with registry.CreateKeyEx(
                registry.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                registry.KEY_SET_VALUE,
            ) as key:
                if enabled:
                    registry.SetValueEx(
                        key,
                        RUN_VALUE_NAME,
                        0,
                        registry.REG_SZ,
                        self.command,
                    )
                else:
                    with suppress(FileNotFoundError):
                        registry.DeleteValue(key, RUN_VALUE_NAME)
        except OSError as exc:
            raise LauncherError(f"Windows自動起動設定を更新できませんでした: {exc}") from exc
        return self.autostart_enabled()

    def open_log_directory(self) -> str:
        self.log_directory.mkdir(parents=True, exist_ok=True)
        try:
            self._folder_opener(str(self.log_directory))
        except OSError as exc:
            raise LauncherError(f"ログフォルダを開けませんでした: {exc}") from exc
        return str(self.log_directory)


def desktop_autostart_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    executable = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{executable.resolve()}" -m app.desktop'


def _winreg() -> Any:
    try:
        import winreg
    except ImportError as exc:
        raise LauncherError("Windows自動起動設定はWindowsでのみ利用できます。") from exc
    return winreg


def _open_folder(path: str) -> None:
    subprocess.Popen(["explorer.exe", path])
