import pytest

from app.actions import ActionExecutor
from app.config import LauncherConfig
from app.errors import ActionNotFoundError


class FakeSwitchBotClient:
    def __init__(self):
        self.calls = []

    async def command_device(self, device_id, command, parameter="default", command_type="command"):
        self.calls.append(("device", device_id, command, parameter, command_type))
        return {"statusCode": 100}

    async def execute_scene(self, scene_id):
        self.calls.append(("scene", scene_id))
        return {"statusCode": 100}


@pytest.mark.asyncio
async def test_execute_device_command():
    config = LauncherConfig.model_validate(
        {
            "buttons": [
                {
                    "id": "light_on",
                    "label": "照明 ON",
                    "type": "device_command",
                    "device_id": "device-1",
                    "command": "turnOn",
                }
            ]
        }
    )
    client = FakeSwitchBotClient()
    executor = ActionExecutor(config, client)

    result = await executor.execute("light_on")

    assert result.success is True
    assert result.label == "照明 ON"
    assert client.calls == [("device", "device-1", "turnOn", "default", "command")]


@pytest.mark.asyncio
async def test_execute_unknown_button():
    config = LauncherConfig.model_validate(
        {
            "buttons": [
                {
                    "id": "scene",
                    "label": "シーン",
                    "type": "scene",
                    "scene_id": "scene-1",
                }
            ]
        }
    )
    executor = ActionExecutor(config, FakeSwitchBotClient())

    with pytest.raises(ActionNotFoundError):
        await executor.execute("missing")
