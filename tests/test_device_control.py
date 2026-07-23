import pytest

from app.device_control import DeviceControlRequest, DeviceControlService
from app.errors import LauncherError


class FakeClient:
    def __init__(self, device_type="Color Bulb"):
        self.device_type = device_type
        self.commands = []

    async def get_devices(self):
        return {
            "body": {
                "deviceList": [
                    {"deviceId": "device-1", "deviceName": "Light", "deviceType": self.device_type}
                ]
            }
        }

    async def command_device(self, device_id, command, parameter="default"):
        self.commands.append((device_id, command, parameter))
        return {"statusCode": 100}


@pytest.mark.asyncio
async def test_controls_power_and_brightness_for_light():
    client = FakeClient()
    service = DeviceControlService(client)

    await service.execute("device-1", DeviceControlRequest(action="turn_on"))
    result = await service.execute(
        "device-1", DeviceControlRequest(action="set_brightness", value=65)
    )

    assert client.commands == [
        ("device-1", "turnOn", "default"),
        ("device-1", "setBrightness", "65"),
    ]
    assert "65%" in result.message


@pytest.mark.asyncio
async def test_rejects_brightness_for_plug():
    service = DeviceControlService(FakeClient("Plug Mini (JP)"))

    with pytest.raises(LauncherError, match="明るさ変更には対応していません"):
        await service.execute(
            "device-1", DeviceControlRequest(action="set_brightness", value=50)
        )


@pytest.mark.asyncio
async def test_presses_bot():
    client = FakeClient("Bot")
    service = DeviceControlService(client)

    await service.execute("device-1", DeviceControlRequest(action="press"))

    assert client.commands == [("device-1", "press", "default")]


@pytest.mark.asyncio
async def test_controls_color_and_color_temperature():
    client = FakeClient("Color Bulb")
    service = DeviceControlService(client)

    await service.execute(
        "device-1", DeviceControlRequest(action="set_color", value="122:80:20")
    )
    await service.execute(
        "device-1", DeviceControlRequest(action="set_color_temperature", value=3200)
    )

    assert client.commands == [
        ("device-1", "setColor", "122:80:20"),
        ("device-1", "setColorTemperature", "3200"),
    ]


@pytest.mark.asyncio
async def test_forced_error_does_not_send_command_or_fetch_devices():
    client = FakeClient()
    service = DeviceControlService(client, force_error=True)

    with pytest.raises(LauncherError, match="SwitchBotへは送信していません"):
        await service.execute("device-1", DeviceControlRequest(action="turn_on"))

    assert client.commands == []
