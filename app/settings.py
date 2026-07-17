import os
from dataclasses import dataclass

from dotenv import load_dotenv

from app.errors import SecretConfigError


@dataclass(frozen=True)
class Settings:
    switchbot_token: str
    switchbot_secret: str
    config_path: str = "config.json"
    host: str = "127.0.0.1"
    port: int = 8765
    force_control_error: bool = False


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv("SWITCHBOT_TOKEN", "").strip()
    secret = os.getenv("SWITCHBOT_SECRET", "").strip()
    if not token or not secret:
        raise SecretConfigError(".env に SWITCHBOT_TOKEN と SWITCHBOT_SECRET を設定してください。")

    return Settings(
        switchbot_token=token,
        switchbot_secret=secret,
        config_path=os.getenv("SWITCHBOT_CONFIG_PATH", "config.json"),
        host=os.getenv("SWITCHBOT_HOST", "127.0.0.1"),
        port=int(os.getenv("SWITCHBOT_PORT", "8765")),
        force_control_error=os.getenv("SWITCHBOT_FORCE_CONTROL_ERROR", "").strip().lower()
        in {"1", "true", "yes", "on"},
    )
