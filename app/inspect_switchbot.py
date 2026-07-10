import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.errors import SwitchBotApiError
from app.settings import load_settings
from app.switchbot_client import SwitchBotClient, SwitchBotCredentials

OUTPUT_PATH = Path("switchbot.inspection.json")


async def inspect_switchbot(output_path: Path = OUTPUT_PATH) -> None:
    settings = load_settings()
    client = SwitchBotClient(
        SwitchBotCredentials(
            token=settings.switchbot_token,
            secret=settings.switchbot_secret,
        )
    )

    devices_response = await client.get_devices()
    scenes_response = await client.get_scenes()
    devices_body = devices_response.get("body", {})
    devices = _collect_devices(devices_body)

    statuses = []
    for device in devices:
        device_id = device.get("deviceId")
        if not device_id:
            continue
        statuses.append(await _get_status_entry(client, device))

    payload = {
        "inspected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "device_count": len(devices),
            "status_success_count": sum(1 for item in statuses if item["ok"]),
            "status_error_count": sum(1 for item in statuses if not item["ok"]),
            "scene_count": len(scenes_response.get("body", [])),
        },
        "devices": devices_body,
        "device_statuses": statuses,
        "scenes": scenes_response.get("body", []),
        "notes": [
            "Open API device status fields differ by device type.",
            "Room classification and app automation definitions may not be exposed by Open API.",
            "Device registration and room assignment changes are not treated as "
            "supported operations here.",
        ],
    }

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Inspected SwitchBot resources to {output_path}")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


def _collect_devices(devices_body: dict[str, Any]) -> list[dict[str, Any]]:
    device_list = devices_body.get("deviceList", [])
    infrared_remote_list = devices_body.get("infraredRemoteList", [])
    return [
        *[dict(device, source="deviceList") for device in device_list],
        *[dict(device, source="infraredRemoteList") for device in infrared_remote_list],
    ]


async def _get_status_entry(
    client: SwitchBotClient,
    device: dict[str, Any],
) -> dict[str, Any]:
    device_id = device["deviceId"]
    try:
        response = await client.get_device_status(device_id)
    except SwitchBotApiError as exc:
        return {
            "ok": False,
            "deviceId": device_id,
            "deviceName": device.get("deviceName"),
            "deviceType": device.get("deviceType"),
            "source": device.get("source"),
            "error": str(exc),
        }
    return {
        "ok": True,
        "deviceId": device_id,
        "deviceName": device.get("deviceName"),
        "deviceType": device.get("deviceType"),
        "source": device.get("source"),
        "body": response.get("body", {}),
    }


def main() -> None:
    asyncio.run(inspect_switchbot())


if __name__ == "__main__":
    main()
