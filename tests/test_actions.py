import pytest

from app.actions import ActionExecutor
from app.config import LauncherConfig
from app.errors import ActionNotFoundError, LauncherError


class FakeSwitchBotClient:
    def __init__(self):
        self.calls = []

    async def command_device(self, device_id, command, parameter="default", command_type="command"):
        self.calls.append(("device", device_id, command, parameter, command_type))
        return {"statusCode": 100}

    async def execute_scene(self, scene_id):
        self.calls.append(("scene", scene_id))
        return {"statusCode": 100}

    async def get_scenes(self):
        self.calls.append(("get_scenes",))
        return {"statusCode": 100, "body": [{"sceneId": "scene-1"}]}


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
async def test_execute_remote_quick_action():
    config = LauncherConfig.model_validate(
        {
            "buttons": [
                {
                    "id": "ac_cool",
                    "label": "冷房25℃",
                    "type": "remote_command",
                    "device_id": "remote-1",
                    "command": "setAll",
                    "parameter": "25,2,1,on",
                }
            ]
        }
    )
    client = FakeSwitchBotClient()

    await ActionExecutor(config, client).execute("ac_cool")

    assert client.calls == [("device", "remote-1", "setAll", "25,2,1,on", "command")]


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


@pytest.mark.asyncio
async def test_locked_scene_is_not_executed():
    config = LauncherConfig.model_validate(
        {
            "buttons": [
                {
                    "id": "dangerous",
                    "label": "危険なシーン",
                    "type": "scene",
                    "scene_id": "scene-1",
                    "locked": True,
                }
            ]
        }
    )
    client = FakeSwitchBotClient()
    executor = ActionExecutor(config, client)

    with pytest.raises(LauncherError, match="操作ロック"):
        await executor.execute("dangerous")
    assert client.calls == []


@pytest.mark.asyncio
async def test_missing_scene_is_not_executed():
    config = LauncherConfig.model_validate(
        {
            "buttons": [
                {
                    "id": "missing_scene",
                    "label": "存在しないシーン",
                    "type": "scene",
                    "scene_id": "missing",
                }
            ]
        }
    )
    client = FakeSwitchBotClient()
    executor = ActionExecutor(config, client)

    with pytest.raises(ActionNotFoundError, match="現在のシーン一覧にありません"):
        await executor.execute("missing_scene")

    assert client.calls == [("get_scenes",)]
