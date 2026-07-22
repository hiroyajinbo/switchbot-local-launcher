import json

import pytest

from app.config import load_config
from app.config_sync import (
    ButtonAppearanceUpdate,
    ConfigSyncService,
    RemoteQuickActionUpdate,
    SceneSyncUpdate,
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


@pytest.mark.asyncio
async def test_refresh_hides_excluded_scene_from_candidates(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [],
                "scene_sync": {
                    "auto_add": False,
                    "excluded_scene_ids": ["scene-1"],
                },
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    result = await service.refresh()

    assert [item.type for item in result.candidates] == ["device_command", "device_command"]
    assert [item.source_id for item in result.excluded_scenes] == ["scene-1"]
    assert result.excluded_scenes[0].label == "Home"


def test_remove_scene_adds_exclusion_and_allows_empty_buttons(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {"id": "home", "label": "Home", "type": "scene", "scene_id": "scene-1"}
                ]
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    result = service.remove_scene("home")
    config = load_config(config_path)

    assert result["excluded"] is True
    assert config.buttons == []
    assert config.scene_sync.excluded_scene_ids == ["scene-1"]
    assert config.scene_sync.excluded_scene_labels == {"scene-1": "Home"}


@pytest.mark.asyncio
async def test_excluded_scene_keeps_saved_label_when_missing_from_switchbot(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {
                        "id": "bath_copy",
                        "label": "お風呂_copy",
                        "type": "scene",
                        "scene_id": "missing-scene",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    service.remove_scene("bath_copy")
    result = await service.refresh()

    assert result.excluded_scenes[0].source_id == "missing-scene"
    assert result.excluded_scenes[0].label == "お風呂_copy"


def test_restore_excluded_scene_returns_it_to_discovery(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [],
                "scene_sync": {
                    "auto_add": False,
                    "excluded_scene_ids": ["scene-1"],
                    "excluded_scene_labels": {"scene-1": "Home"},
                },
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    result = service.restore_scene("scene-1")

    assert result == {"scene_id": "scene-1", "excluded": False}
    config = load_config(config_path)
    assert config.scene_sync.excluded_scene_ids == []
    assert config.scene_sync.excluded_scene_labels == {}


@pytest.mark.asyncio
async def test_auto_add_adds_only_scenes_and_leaves_device_candidates(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [],
                "scene_sync": {"auto_add": True, "excluded_scene_ids": []},
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    result = await service.refresh()

    assert result.auto_added == 1
    assert [item.type for item in result.candidates] == ["device_command", "device_command"]
    assert [button.scene_id for button in load_config(config_path).buttons] == ["scene-1"]


@pytest.mark.asyncio
async def test_scene_id_prevents_duplicate_candidate_after_scene_rename(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {
                        "id": "old_name",
                        "label": "Old name",
                        "type": "scene",
                        "scene_id": "scene-1",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    result = await service.refresh()

    assert all(item.type != "scene" for item in result.candidates)


def test_updates_scene_auto_add_setting(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"buttons": []}', encoding="utf-8")
    service = ConfigSyncService(config_path, FakeClient())

    result = service.update_scene_sync(SceneSyncUpdate(auto_add=True))

    assert result == {"auto_add": True}
    assert load_config(config_path).scene_sync.auto_add is True


def test_updates_button_appearance(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "quick_action_groups": ["扇風機"],
                "buttons": [
                    {"id": "fan_up", "label": "Fan", "type": "scene", "scene_id": "scene-1"}
                ]
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    result = service.set_button_appearance(
        "fan_up",
        ButtonAppearanceUpdate(icon="fan", icon_badge="up", group="扇風機"),
    )

    assert result == {
        "id": "fan_up",
        "icon": "fan",
        "icon_badge": "up",
        "group": "扇風機",
    }
    button = load_config(config_path).buttons[0]
    assert button.icon == "fan"
    assert button.icon_badge == "up"
    assert button.group == "扇風機"


def test_saves_and_overwrites_remote_quick_action(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "quick_action_groups": ["空調"],
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
            }
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
            {
                "quick_action_groups": ["空調"],
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
            }
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


def test_updates_remote_quick_action_in_place_and_preserves_lock(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "quick_action_groups": ["Air", "Living"],
                "buttons": [
                    {"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"},
                    {
                        "id": "remote_old",
                        "label": "AC 24",
                        "group": "Air",
                        "type": "remote_command",
                        "device_id": "remote-1",
                        "command": "setAll",
                        "parameter": "24,2,1,on",
                        "locked": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    result = service.update_remote_quick_action(
        "remote_old",
        RemoteQuickActionUpdate(
            label="AC 26",
            group="Living",
            device_id="remote-1",
            parameter="26,2,3,on",
            icon="fan",
        ),
    )

    config = load_config(config_path)
    assert result["previous_id"] == "remote_old"
    assert [button.type for button in config.buttons] == ["scene", "remote_command"]
    saved = config.buttons[1]
    assert saved.id == result["id"]
    assert saved.label == "AC 26"
    assert saved.group == "Living"
    assert saved.parameter == "26,2,3,on"
    assert saved.locked is True
    assert saved.icon == "fan"


def test_removes_only_manual_remote_quick_actions(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"},
                    {
                        "id": "remote_off",
                        "label": "AC OFF",
                        "type": "remote_command",
                        "device_id": "remote-1",
                        "command": "turnOff",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    result = service.remove_remote_quick_action("remote_off")

    assert result["removed"] is True
    assert [button.id for button in load_config(config_path).buttons] == ["scene"]
    with pytest.raises(ConfigError, match="リモコン操作だけ"):
        service.remove_remote_quick_action("scene")


def test_manages_quick_action_groups_and_preserves_legacy_groups(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "quick_action_groups": ["空調"],
                "buttons": [
                    {
                        "id": "scene_bath",
                        "label": "Bath",
                        "group": "お風呂",
                        "type": "scene",
                        "scene_id": "scene-1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    assert service.quick_action_groups() == ["空調", "お風呂", "シーン"]
    assert service.add_quick_action_group(" モニター ") == [
        "空調", "お風呂", "シーン", "モニター"
    ]
    assert service.reorder_quick_action_groups(
        ["シーン", "モニター", "空調", "お風呂"]
    ) == ["シーン", "モニター", "空調", "お風呂"]
    assert load_config(config_path).quick_action_groups == [
        "シーン", "モニター", "空調", "お風呂"
    ]


def test_removing_quick_action_group_moves_scene_and_remote_to_default(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "quick_action_groups": ["シーン", "空調"],
                "buttons": [
                    {
                        "id": "scene_home",
                        "label": "Home",
                        "group": "空調",
                        "type": "scene",
                        "scene_id": "scene-1",
                    },
                    {
                        "id": "remote_off",
                        "label": "AC OFF",
                        "group": "空調",
                        "type": "remote_command",
                        "device_id": "remote-1",
                        "command": "turnOff",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    result = service.remove_quick_action_group("空調")

    assert result == {"removed": "空調", "moved_buttons": 2, "groups": ["シーン"]}
    assert [button.group for button in load_config(config_path).buttons] == ["シーン", "シーン"]
    with pytest.raises(ConfigError, match="削除できません"):
        service.remove_quick_action_group("シーン")


def test_rejects_unregistered_quick_action_group(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "quick_action_groups": ["シーン"],
                "buttons": [
                    {
                        "id": "scene_home",
                        "label": "Home",
                        "group": "シーン",
                        "type": "scene",
                        "scene_id": "scene-1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    service = ConfigSyncService(config_path, FakeClient())

    with pytest.raises(ConfigError, match="先にクイック操作グループ"):
        service.set_button_appearance(
            "scene_home",
            ButtonAppearanceUpdate(icon="scene", icon_badge="none", group="未登録"),
        )
