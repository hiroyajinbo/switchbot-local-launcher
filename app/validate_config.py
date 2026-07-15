import argparse
import json
from pathlib import Path
from typing import Any

from app.config import DeviceCommandButton, SceneButton, load_config
from app.errors import ConfigError

DEFAULT_CONFIG_PATH = Path("config.json")
DEFAULT_RESOURCES_PATH = Path("switchbot.resources.json")


def validate_references(config_path: Path, resources_path: Path) -> list[str]:
    config = load_config(config_path)
    try:
        resources = json.loads(resources_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(
            f"リソース一覧が見つかりません: {resources_path}。"
            " python -m app.export_resources を先に実行してください。"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"リソース一覧がJSONとして読めません: {exc.msg}") from exc

    device_ids = _device_ids(resources)
    scene_ids = _scene_ids(resources)
    errors = []
    for button in config.buttons:
        if isinstance(button, SceneButton) and button.scene_id not in scene_ids:
            errors.append(
                f"{button.id}: scene_id '{button.scene_id}' は現在のシーン一覧にありません。"
            )
        elif isinstance(button, DeviceCommandButton) and button.device_id not in device_ids:
            errors.append(
                f"{button.id}: device_id '{button.device_id}' は現在のデバイス一覧にありません。"
            )
    return errors


def _device_ids(resources: dict[str, Any]) -> set[str]:
    devices = resources.get("devices", {})
    if not isinstance(devices, dict):
        return set()
    device_list = devices.get("deviceList", [])
    if not isinstance(device_list, list):
        return set()
    return {
        item["deviceId"]
        for item in device_list
        if isinstance(item, dict) and isinstance(item.get("deviceId"), str)
    }


def _scene_ids(resources: dict[str, Any]) -> set[str]:
    scenes = resources.get("scenes", [])
    if not isinstance(scenes, list):
        return set()
    return {
        item["sceneId"]
        for item in scenes
        if isinstance(item, dict) and isinstance(item.get("sceneId"), str)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate config IDs against exported resources.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--resources", default=str(DEFAULT_RESOURCES_PATH))
    args = parser.parse_args()

    try:
        errors = validate_references(Path(args.config), Path(args.resources))
    except ConfigError as exc:
        parser.exit(2, f"ERROR: {exc}\n")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        parser.exit(1, f"Validation failed with {len(errors)} error(s).\n")
    print("Config validation passed: all scene_id and device_id references exist.")


if __name__ == "__main__":
    main()
