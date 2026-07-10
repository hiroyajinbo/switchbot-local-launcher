import json

import pytest

from app.config import DeviceCommandButton, SceneButton, load_config
from app.errors import ConfigError


def test_load_config_reads_device_and_scene_buttons(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {
                        "id": "light_on",
                        "label": "照明 ON",
                        "type": "device_command",
                        "device_id": "device-1",
                        "command": "turnOn",
                    },
                    {
                        "id": "leaving_home",
                        "label": "いってきます",
                        "type": "scene",
                        "scene_id": "scene-1",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config.buttons[0], DeviceCommandButton)
    assert config.buttons[0].parameter == "default"
    assert isinstance(config.buttons[1], SceneButton)


def test_load_config_rejects_invalid_json(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{", encoding="utf-8")

    with pytest.raises(ConfigError, match="JSON"):
        load_config(config_path)


def test_load_config_rejects_duplicate_button_ids(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {
                        "id": "same",
                        "label": "照明 ON",
                        "type": "device_command",
                        "device_id": "device-1",
                        "command": "turnOn",
                    },
                    {
                        "id": "same",
                        "label": "照明 OFF",
                        "type": "device_command",
                        "device_id": "device-1",
                        "command": "turnOff",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="重複"):
        load_config(config_path)


def test_load_config_explains_when_resource_export_is_used(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "exported_at": "2026-07-10 21:18:56",
                "devices": {"deviceList": []},
                "scenes": [],
                "config_hints": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="そのまま config.json として使えません"):
        load_config(config_path)
