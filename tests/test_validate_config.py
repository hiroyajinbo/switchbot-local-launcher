import json

from app.validate_config import validate_references


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_validate_references_accepts_exported_ids(tmp_path):
    config_path = tmp_path / "config.json"
    resources_path = tmp_path / "resources.json"
    _write_json(
        config_path,
        {
            "buttons": [
                {"id": "scene", "label": "Scene", "type": "scene", "scene_id": "scene-1"},
                {
                    "id": "light",
                    "label": "Light",
                    "type": "device_command",
                    "device_id": "device-1",
                    "command": "turnOn",
                },
            ]
        },
    )
    _write_json(
        resources_path,
        {
            "scenes": [{"sceneId": "scene-1"}],
            "devices": {"deviceList": [{"deviceId": "device-1"}]},
        },
    )

    assert validate_references(config_path, resources_path) == []


def test_validate_references_reports_unknown_ids(tmp_path):
    config_path = tmp_path / "config.json"
    resources_path = tmp_path / "resources.json"
    _write_json(
        config_path,
        {
            "buttons": [
                {"id": "bad_scene", "label": "Bad", "type": "scene", "scene_id": "missing"}
            ]
        },
    )
    _write_json(resources_path, {"scenes": [], "devices": {"deviceList": []}})

    errors = validate_references(config_path, resources_path)

    assert errors == ["bad_scene: scene_id 'missing' は現在のシーン一覧にありません。"]
