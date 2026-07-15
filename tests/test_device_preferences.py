import json

from app.device_preferences import (
    DevicePreferenceService,
    DevicePreferenceUpdate,
    LightPresetUpdate,
)


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
