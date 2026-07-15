import argparse
import json
import re
from pathlib import Path
from typing import Any

from app.config import LauncherConfig

DEFAULT_INPUT_PATH = Path("switchbot.resources.json")
DEFAULT_OUTPUT_PATH = Path("config.device-buttons.generated.json")

ON_OFF_DEVICE_TYPES = {
    "Ceiling Light",
    "Color Bulb",
    "Plug Mini (JP)",
    "Strip Light",
}


def build_device_command_config(resources: dict[str, Any]) -> dict[str, Any]:
    devices = resources.get("devices", {}).get("deviceList", [])
    if not isinstance(devices, list):
        devices = []

    buttons = []
    for index, device in enumerate(devices, start=1):
        if not isinstance(device, dict):
            continue
        device_type = device.get("deviceType")
        device_id = device.get("deviceId")
        device_name = device.get("deviceName") or f"Device {index}"
        if device_type not in ON_OFF_DEVICE_TYPES or not device_id:
            continue
        buttons.extend(_on_off_buttons(device_name, device_id, index))

    return {"buttons": buttons}


def write_device_command_template(input_path: Path, output_path: Path) -> int:
    resources = json.loads(input_path.read_text(encoding="utf-8"))
    config = build_device_command_config(resources)
    LauncherConfig.model_validate(config)
    output_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(config["buttons"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()

    count = write_device_command_template(Path(args.input), Path(args.output))
    print(f"Generated {args.output} with {count} device command button(s).")
    print("Review it, then copy the buttons you want into config.json.")


def _on_off_buttons(device_name: str, device_id: str, index: int) -> list[dict[str, Any]]:
    base_id = _button_id(device_name, index)
    return [
        {
            "id": f"{base_id}_on",
            "label": f"{device_name} ON",
            "group": "デバイス",
            "type": "device_command",
            "device_id": device_id,
            "command": "turnOn",
            "parameter": "default",
            "command_type": "command",
        },
        {
            "id": f"{base_id}_off",
            "label": f"{device_name} OFF",
            "group": "デバイス",
            "type": "device_command",
            "device_id": device_id,
            "command": "turnOff",
            "parameter": "default",
            "command_type": "command",
        },
    ]


def _button_id(label: str, index: int) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_").lower()
    if not normalized or normalized[0].isdigit():
        normalized = f"device_{index:03d}"
    return normalized


if __name__ == "__main__":
    main()
