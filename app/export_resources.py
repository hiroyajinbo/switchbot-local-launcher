import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.settings import load_settings
from app.switchbot_client import SwitchBotClient, SwitchBotCredentials

OUTPUT_PATH = Path("switchbot.resources.json")


async def export_resources(output_path: Path = OUTPUT_PATH) -> None:
    settings = load_settings()
    client = SwitchBotClient(
        SwitchBotCredentials(
            token=settings.switchbot_token,
            secret=settings.switchbot_secret,
        )
    )
    devices = await client.get_devices()
    scenes = await client.get_scenes()
    payload = {
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "devices": devices.get("body", {}),
        "scenes": scenes.get("body", []),
        "config_hints": {
            "device_command": {
                "type": "device_command",
                "command": "turnOn",
                "parameter": "default",
                "command_type": "command",
            },
            "scene": {
                "type": "scene",
            },
        },
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Exported SwitchBot resources to {output_path}")


def main() -> None:
    asyncio.run(export_resources())


if __name__ == "__main__":
    main()
