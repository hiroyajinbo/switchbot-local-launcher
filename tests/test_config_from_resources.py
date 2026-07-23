import json

from app.config_from_resources import build_config_from_resources, write_config_template


def test_build_config_from_resources_converts_scenes_only():
    config = build_config_from_resources(
        {
            "scenes": [
                {
                    "sceneId": "scene-1",
                    "sceneName": "Leaving Home",
                },
                {
                    "sceneId": "scene-2",
                    "sceneName": "お風呂",
                },
            ],
            "devices": {"deviceList": [{"deviceId": "device-1"}]},
        }
    )

    assert config == {
        "buttons": [
            {
                "id": "scene_leaving_home",
                "label": "Leaving Home",
                "group": "シーン",
                "type": "scene",
                "scene_id": "scene-1",
            },
            {
                "id": "scene_002",
                "label": "お風呂",
                "group": "シーン",
                "type": "scene",
                "scene_id": "scene-2",
            },
        ]
    }


def test_write_config_template_writes_valid_launcher_config(tmp_path):
    input_path = tmp_path / "switchbot.resources.json"
    output_path = tmp_path / "config.generated.json"
    input_path.write_text(
        json.dumps({"scenes": [{"sceneId": "scene-1", "sceneName": "Leaving Home"}]}),
        encoding="utf-8",
    )

    count = write_config_template(input_path, output_path)

    assert count == 1
    assert json.loads(output_path.read_text(encoding="utf-8"))["buttons"][0]["type"] == "scene"
