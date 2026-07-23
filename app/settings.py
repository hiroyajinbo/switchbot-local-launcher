import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

from app.credential_store import CredentialStore, WindowsCredentialStore
from app.errors import SecretConfigError


@dataclass(frozen=True)
class Settings:
    switchbot_token: str
    switchbot_secret: str
    config_path: str = "config.json"
    host: str = "127.0.0.1"
    port: int = 8765
    log_path: str = "logs/switchbot-local-launcher.log"
    force_control_error: bool = False
    credentials_source: Literal["env", "windows", "missing"] = "env"


def load_settings(
    env_path: str | Path | None = None,
    *,
    credential_store: CredentialStore | None = None,
    allow_missing_credentials: bool = False,
) -> Settings:
    load_dotenv(dotenv_path=env_path)
    token = os.getenv("SWITCHBOT_TOKEN", "").strip()
    secret = os.getenv("SWITCHBOT_SECRET", "").strip()
    credentials_source: Literal["env", "windows", "missing"] = "env"

    if not token or not secret:
        store = credential_store or WindowsCredentialStore()
        stored = store.load() if store.available else None
        if stored is not None:
            token = stored.token
            secret = stored.secret
            credentials_source = "windows"
        elif allow_missing_credentials:
            token = ""
            secret = ""
            credentials_source = "missing"
        else:
            raise SecretConfigError(
                "SwitchBotのOpen TokenとSecret Keyを初回設定してください。"
            )

    return Settings(
        switchbot_token=token,
        switchbot_secret=secret,
        config_path=os.getenv("SWITCHBOT_CONFIG_PATH", "config.json"),
        host=os.getenv("SWITCHBOT_HOST", "127.0.0.1"),
        port=int(os.getenv("SWITCHBOT_PORT", "8765")),
        log_path=os.getenv("SWITCHBOT_LOG_PATH", "logs/switchbot-local-launcher.log"),
        force_control_error=os.getenv("SWITCHBOT_FORCE_CONTROL_ERROR", "").strip().lower()
        in {"1", "true", "yes", "on"},
        credentials_source=credentials_source,
    )
