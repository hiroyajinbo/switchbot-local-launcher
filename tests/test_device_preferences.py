import json

import pytest

from app.device_preferences import (
    DevicePreferenceService,
    DevicePreferenceUpdate,
    LightPresetUpdate,
)
from app.errors import LauncherError


def test_updates_device_preference_without_removing_buttons(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {"buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}]}
        ),
        encoding="utf-8",
    )

    result = DevicePreferenceService(path).update(
        "device-1", DevicePreferenceUpdate(room="リビング", icon="light", locked=True)
    )
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert result.locked is True
    assert saved["buttons"][0]["id"] == "scene"
    assert saved["device_preferences"]["device-1"]["room"] == "リビング"


def test_adds_room_only_once(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {"buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}]}
        ),
        encoding="utf-8",
    )
    service = DevicePreferenceService(path)

    service.add_room("寝室")
    rooms = service.add_room("寝室")

    assert rooms == ["未分類", "寝室"]


def test_adds_new_room_after_preference_only_rooms(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
                "device_preferences": {
                    "sensor-1": {"room": "トイレ", "icon": "sensor", "locked": False}
                },
            }
        ),
        encoding="utf-8",
    )

    rooms = DevicePreferenceService(path).add_room("新しい部屋")

    assert rooms == ["未分類", "トイレ", "新しい部屋"]


def test_saves_light_preset(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {"buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}]}
        ),
        encoding="utf-8",
    )
    service = DevicePreferenceService(path)

    service.add_preset(
        "light-1",
        LightPresetUpdate(name="読書", brightness=60, color_temperature=3200),
    )

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["light_presets"]["light-1"][0]["name"] == "読書"


def test_removes_light_preset_and_empty_device_entry(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
                "light_presets": {
                    "light-1": [{"name": "読書", "brightness": 60, "color_temperature": 3200}]
                },
            }
        ),
        encoding="utf-8",
    )
    service = DevicePreferenceService(path)

    assert service.remove_preset("light-1", "読書") is True
    assert service.remove_preset("light-1", "存在しない") is False
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "light-1" not in saved["light_presets"]


def test_reorders_rooms(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
                "rooms": ["未分類", "リビング", "寝室"],
            }
        ),
        encoding="utf-8",
    )

    rooms = DevicePreferenceService(path).reorder_rooms(["リビング", "寝室", "未分類"])

    assert rooms == ["リビング", "寝室", "未分類"]
    assert json.loads(path.read_text(encoding="utf-8"))["rooms"] == rooms


def test_updates_light_preset_in_place(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
                "light_presets": {"light-1": [{"name": "読書", "brightness": 60}]},
            }
        ),
        encoding="utf-8",
    )
    service = DevicePreferenceService(path)

    result = service.update_preset(
        "light-1", "読書", LightPresetUpdate(name="夜", brightness=25, color_temperature=2700)
    )

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert result.name == "夜"
    assert saved["light_presets"]["light-1"] == [
        {"name": "夜", "brightness": 25, "color": None, "color_temperature": 2700}
    ]


def test_removes_empty_room(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
                "rooms": ["未分類", "空き部屋"],
            }
        ),
        encoding="utf-8",
    )

    result = DevicePreferenceService(path).remove_room("空き部屋")

    assert result == {"removed": "空き部屋", "moved_devices": 0, "rooms": ["未分類"]}


def test_removes_room_and_moves_devices_without_losing_preferences(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
                "rooms": ["未分類", "寝室"],
                "device_preferences": {
                    "light-1": {"room": "寝室", "icon": "light", "locked": True},
                    "plug-1": {"room": "未分類", "icon": "plug", "locked": False},
                },
                "light_presets": {
                    "light-1": [{"name": "就寝", "brightness": 20}]
                },
            }
        ),
        encoding="utf-8",
    )

    result = DevicePreferenceService(path).remove_room("寝室")
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert result["moved_devices"] == 1
    assert saved["device_preferences"]["light-1"] == {
        "room": "未分類", "icon": "light", "locked": True
    }
    assert saved["light_presets"]["light-1"][0]["name"] == "就寝"


def test_refuses_to_remove_uncategorized_room(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {"buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}]}
        ),
        encoding="utf-8",
    )

    with pytest.raises(LauncherError, match="未分類.*削除できません"):
        DevicePreferenceService(path).remove_room("未分類")


def test_includes_and_persists_room_from_device_preference(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
                "device_preferences": {
                    "light-1": {"room": "旧設定の部屋", "icon": "light", "locked": False}
                },
            }
        ),
        encoding="utf-8",
    )
    service = DevicePreferenceService(path)

    assert service.rooms() == ["未分類", "旧設定の部屋"]
    service.reorder_rooms(["旧設定の部屋", "未分類"])

    assert json.loads(path.read_text(encoding="utf-8"))["rooms"] == ["旧設定の部屋", "未分類"]


def test_excludes_and_restores_device_without_losing_settings(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
                "device_preferences": {
                    "light-1": {"room": "寝室", "icon": "light", "locked": True}
                },
                "light_presets": {"light-1": [{"name": "就寝", "brightness": 20}]},
            }
        ),
        encoding="utf-8",
    )
    service = DevicePreferenceService(path)

    excluded = service.exclude_device("light-1", "寝室照明")
    restored = service.restore_device("light-1")
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert excluded["devices"] == [{"device_id": "light-1", "label": "寝室照明"}]
    assert restored["devices"] == []
    assert saved["device_preferences"]["light-1"] == {
        "room": "寝室", "icon": "light", "locked": True
    }
    assert saved["light_presets"]["light-1"][0]["name"] == "就寝"
    with pytest.raises(LauncherError, match="見つかりません"):
        service.restore_device("light-1")
