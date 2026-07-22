from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from app.credential_store import CredentialStore
from app.errors import LauncherError
from app.settings import Settings, load_settings

APP_DATA_DIRECTORY = "SwitchBotLocalLauncher"
PORTABLE_DATA_ROOT_ENV = "SWITCHBOT_PORTABLE_DATA_ROOT"


@dataclass(frozen=True)
class AppDataPaths:
    root: Path

    @property
    def env(self) -> Path:
        return self.root / ".env"

    @property
    def config(self) -> Path:
        return self.root / "config.json"

    @property
    def log(self) -> Path:
        return self.root / "logs" / "switchbot-local-launcher.log"


def desktop_data_paths(environ: Mapping[str, str] | None = None) -> AppDataPaths:
    values = environ or os.environ
    portable_root = values.get(PORTABLE_DATA_ROOT_ENV, "").strip()
    if portable_root:
        return AppDataPaths(Path(portable_root))

    local_app_data = values.get("LOCALAPPDATA", "").strip()
    if not local_app_data:
        raise LauncherError("LOCALAPPDATAが見つからないため、PCアプリの保存先を作成できません。")
    return AppDataPaths(Path(local_app_data) / APP_DATA_DIRECTORY)


def prepare_desktop_data(
    source_directory: Path | None = None,
    *,
    paths: AppDataPaths | None = None,
) -> AppDataPaths:
    source = (source_directory or Path.cwd()).resolve()
    paths = paths or desktop_data_paths()
    paths.root.mkdir(parents=True, exist_ok=True)
    _copy_if_missing(source / ".env", paths.env)
    _copy_if_missing(source / "config.json", paths.config)

    missing = [str(paths.config)] if not paths.config.exists() else []
    if missing:
        raise LauncherError(
            "PCアプリの設定ファイルがありません。開発版のconfig.jsonを用意して"
            f"再起動してください: {', '.join(missing)}"
        )
    return paths


def load_desktop_settings(
    paths: AppDataPaths,
    *,
    credential_store: CredentialStore | None = None,
    allow_missing_credentials: bool = False,
) -> Settings:
    settings = load_settings(
        env_path=paths.env,
        credential_store=credential_store,
        allow_missing_credentials=allow_missing_credentials,
    )
    config_path = _resolve_data_path(settings.config_path, paths.root)
    log_path = _resolve_data_path(settings.log_path, paths.root)
    return replace(settings, config_path=str(config_path), log_path=str(log_path))


def _copy_if_missing(source: Path, destination: Path) -> None:
    if destination.exists() or not source.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _resolve_data_path(value: str, root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path
