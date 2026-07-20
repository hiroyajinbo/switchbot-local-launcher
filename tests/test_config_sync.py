import json

import pytest

from app.config import load_config
from app.config_sync import (
    ButtonAppearanceUpdate,
    ConfigSyncService,
    RemoteQuickActionUpdate,
)
from app.errors import ConfigError


class FakeClient:
    async def get_devices(self):
        return {
            "body": {
                "deviceList": [
                    {
                        "deviceId": "light-1",
                        "deviceName": "Light",
                        "deviceType": "Color Bulb",
                    }
                ]
            }
        }

    async def get_scenes(self):
        return {"body": [{"sceneId": "scene-1", "sceneName": "Home"}]}


@pytest.mark.asyncio
async def test_refresh_and_apply_candidates_preserves_existing_config(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {"id": "existing", "label": "Existing", "type": "scene", "scene_id": "old"}
                ]
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    candidates = await service.refresh()
    result = service.apply(["scene_home", "light_on"])

    assert {candidate.id for candidate in candidates.candidates} == {
        "scene_home",
        "light_on",
        "light_off",
    }
    assert result.added == 2
    assert [candidate.id for candidate in candidates.stale] == ["existing"]
    assert [button.id for button in load_config(config_path).buttons] == [
        "existing",
        "scene_home",
        "light_on",
    ]


@pytest.mark.asyncio
async def test_apply_rejects_id_not_in_latest_candidates(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {"id": "existing", "label": "X", "type": "scene", "scene_id": "x"}
                ]
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())
    await service.refresh()

    with pytest.raises(ConfigError, match="取得候補にない"):
        service.apply(["unknown"])


@pytest.mark.asyncio
async def test_removes_selected_stale_button(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {"id": "valid", "label": "Valid", "type": "scene", "scene_id": "scene-1"},
                    {"id": "stale", "label": "Stale", "type": "scene", "scene_id": "missing"},
                ]
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())
    candidates = await service.refresh()

    result = service.remove_buttons([candidates.stale[0].id])

    assert result == {"removed": 1}
    assert [button.id for button in load_config(config_path).buttons] == ["valid"]


def test_updates_button_appearance(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {"id": "fan_up", "label": "Fan", "type": "scene", "scene_id": "scene-1"}
                ]
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    result = service.set_button_appearance(
        "fan_up", ButtonAppearanceUpdate(icon="fan", icon_badge="up")
    )

    assert result == {"id": "fan_up", "icon": "fan", "icon_badge": "up"}
    button = load_config(config_path).buttons[0]
    assert button.icon == "fan"
    assert button.icon_badge == "up"


def test_saves_and_overwrites_remote_quick_action(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {"buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}]}
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())
    update = RemoteQuickActionUpdate(
        label="寝る前の冷房",
        group="空調",
        device_id="remote-1",
        parameter="25,2,1,on",
    )

    added = service.save_remote_quick_action(update)
    with pytest.raises(ConfigError, match="登録済み"):
        service.save_remote_quick_action(update)
    updated = service.save_remote_quick_action(
        update.model_copy(update={"label": "冷房25℃", "overwrite": True})
    )

    assert added["updated"] is False
    assert updated == {"id": added["id"], "updated": True}
    saved = load_config(config_path).get_button(added["id"])
    assert saved.type == "remote_command"
    assert saved.label == "冷房25℃"
    assert saved.parameter == "25,2,1,on"


def test_remote_power_off_does_not_depend_on_air_conditioner_settings(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {"buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}]}
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    result = service.save_remote_quick_action(
        RemoteQuickActionUpdate(
            label="エアコンOFF",
            group="空調",
            device_id="remote-1",
            command="turnOff",
            parameter="default",
        )
    )

    saved = load_config(config_path).get_button(result["id"])
    assert saved.command == "turnOff"
    assert saved.parameter == "default"
