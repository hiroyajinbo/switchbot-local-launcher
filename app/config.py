import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.errors import ConfigError


class DeviceCommandButton(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")]
    label: Annotated[str, Field(min_length=1)]
    type: Literal["device_command"]
    device_id: Annotated[str, Field(min_length=1)]
    command: Annotated[str, Field(min_length=1)]
    parameter: str = "default"
    command_type: str = "command"


class SceneButton(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")]
    label: Annotated[str, Field(min_length=1)]
    type: Literal["scene"]
    scene_id: Annotated[str, Field(min_length=1)]


Button = Annotated[DeviceCommandButton | SceneButton, Field(discriminator="type")]


class LauncherConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    buttons: Annotated[list[Button], Field(min_length=1)]

    def get_button(self, button_id: str) -> Button | None:
        return next((button for button in self.buttons if button.id == button_id), None)


def load_config(path: str | Path) -> LauncherConfig:
    config_path = Path(path)
    try:
        raw_config = json.loads(config_path.read_text(encoding="utf-8"))
        if _looks_like_resource_export(raw_config):
            raise ConfigError(
                "switchbot.resources.json はそのまま config.json として使えません。"
                " python -m app.config_from_resources で config.generated.json を作成し、"
                "必要なボタンを config.json にコピーしてください。"
            )
        config = LauncherConfig.model_validate(raw_config)
    except FileNotFoundError as exc:
        raise ConfigError(f"設定ファイルが見つかりません: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"設定ファイルがJSONとして読めません: {exc.msg}") from exc
    except ValidationError as exc:
        raise ConfigError(f"設定ファイルの形式が不正です: {exc}") from exc

    button_ids = [button.id for button in config.buttons]
    duplicated = sorted({button_id for button_id in button_ids if button_ids.count(button_id) > 1})
    if duplicated:
        raise ConfigError(f"ボタンIDが重複しています: {', '.join(duplicated)}")

    return config


def _looks_like_resource_export(value: object) -> bool:
    return (
        isinstance(value, dict)
        and "buttons" not in value
        and {"exported_at", "devices", "scenes"}.issubset(value.keys())
    )
