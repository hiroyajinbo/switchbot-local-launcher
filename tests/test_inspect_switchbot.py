import json

import pytest

import app.inspect_switchbot as inspect_module
from app.settings import Settings


class FakeSwitchBotClient:
    def __init__(self, credentials):
        self.credentials = credentials

    async def get_devices(self):
        return {
            "statusCode": 100,
            "body": {
                "deviceList": [
                    {
                        "deviceId": "device-1",
                        "deviceName": "Hub",
                        "deviceType": "Hub 2",
                    }
                ],
                "infraredRemoteList": [
                    {
                        "deviceId": "remote-1",
                        "deviceName": "Air Conditioner",
                        "deviceType": "Air Conditioner",
                    }
                ],
            },
        }

    async def get_scenes(self):
        return {"statusCode": 100, "body": [{"sceneId": "scene-1"}]}

    async def get_device_status(self, device_id):
        return {"statusCode": 100, "body": {"deviceId": device_id, "power": "on"}}


@pytest.mark.asyncio
async def test_inspect_switchbot_writes_statuses(tmp_path, monkeypatch):
    output_path = tmp_path / "switchbot.inspection.json"
    monkeypatch.setattr(
        inspect_module,
        "load_settings",
        lambda: Settings(switchbot_token="token", switchbot_secret="secret"),
    )
    monkeypatch.setattr(inspect_module, "SwitchBotClient", FakeSwitchBotClient)

    await inspect_module.inspect_switchbot(output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["device_count"] == 2
    assert payload["summary"]["status_success_count"] == 2
    assert payload["summary"]["scene_count"] == 1
    assert payload["device_statuses"][0]["body"]["power"] == "on"
