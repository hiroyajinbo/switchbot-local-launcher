import json

import pytest

import app.export_resources as export_module
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
                        "deviceName": "Living Light",
                        "deviceType": "Light",
                    }
                ]
            },
        }

    async def get_scenes(self):
        return {
            "statusCode": 100,
            "body": [
                {
                    "sceneId": "scene-1",
                    "sceneName": "Leaving Home",
                }
            ],
        }


@pytest.mark.asyncio
async def test_export_resources_writes_devices_and_scenes(tmp_path, monkeypatch):
    output_path = tmp_path / "switchbot.resources.json"
    monkeypatch.setattr(
        export_module,
        "load_settings",
        lambda: Settings(switchbot_token="token", switchbot_secret="secret"),
    )
    monkeypatch.setattr(export_module, "SwitchBotClient", FakeSwitchBotClient)

    await export_module.export_resources(output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["devices"]["deviceList"][0]["deviceId"] == "device-1"
    assert payload["scenes"][0]["sceneId"] == "scene-1"
    assert payload["config_hints"]["device_command"]["command"] == "turnOn"
