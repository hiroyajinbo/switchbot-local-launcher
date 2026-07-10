import json

from app.config_device_commands import build_device_command_config, write_device_command_template


def test_build_device_command_config_generates_on_off_for_supported_devices():
    config = build_device_command_config(
        {
            "devices": {
                "deviceList": [
                    {
                        "deviceId": "light-1",
                        "deviceName": "Living Light",
                        "deviceType": "Color Bulb",
                    },
                    {
                        "deviceId": "bot-1",
                        "deviceName": "Bath",
                        "deviceType": "Bot",
                    },
                    {
                        "deviceId": "plug-1",
                        "deviceName": "Kettle",
                        "deviceType": "Plug Mini (JP)",
                    },
                ]
            }
        }
    )

    assert config["buttons"] == [
        {
            "id": "living_light_on",
            "label": "Living Light ON",
            "type": "device_command",
            "device_id": "light-1",
            "command": "turnOn",
            "parameter": "default",
            "command_type": "command",
        },
        {
            "id": "living_light_off",
            "label": "Living Light OFF",
            "type": "device_command",
            "device_id": "light-1",
            "command": "turnOff",
            "parameter": "default",
            "command_type": "command",
        },
        {
            "id": "kettle_on",
            "label": "Kettle ON",
            "type": "device_command",
            "device_id": "plug-1",
            "command": "turnOn",
            "parameter": "default",
            "command_type": "command",
        },
        {
            "id": "kettle_off",
            "label": "Kettle OFF",
            "type": "device_command",
            "device_id": "plug-1",
            "command": "turnOff",
            "parameter": "default",
            "command_type": "command",
        },
    ]


def test_write_device_command_template_writes_valid_launcher_config(tmp_path):
    input_path = tmp_path / "switchbot.resources.json"
    output_path = tmp_path / "config.device-buttons.generated.json"
    input_path.write_text(
        json.dumps(
            {
                "devices": {
                    "deviceList": [
                        {
                            "deviceId": "light-1",
                            "deviceName": "Living Light",
                            "deviceType": "Color Bulb",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    count = write_device_command_template(input_path, output_path)

    assert count == 2
    assert json.loads(output_path.read_text(encoding="utf-8"))["buttons"][0]["command"] == "turnOn"


def test_build_device_command_config_uses_safe_id_for_numeric_name():
    config = build_device_command_config(
        {
            "devices": {
                "deviceList": [
                    {
                        "deviceId": "light-1",
                        "deviceName": "照明1",
                        "deviceType": "Ceiling Light",
                    }
                ]
            }
        }
    )

    assert config["buttons"][0]["id"] == "device_001_on"
