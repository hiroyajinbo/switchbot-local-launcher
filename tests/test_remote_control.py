import pytest

from app.errors import LauncherError
from app.remote_control import AirConditionerControlRequest, RemoteControlService


class FakeClient:
    def __init__(self, remote_type="Air Conditioner"):
        self.remote_type = remote_type
        self.commands = []

    async def get_devices(self):
        return {
            "body": {
                "infraredRemoteList": [
                    {
                        "deviceId": "remote-1",
                        "deviceName": "Living AC",
                        "remoteType": self.remote_type,
                    }
                ]
            }
        }

    async def command_device(self, device_id, command, parameter="default"):
        self.commands.append((device_id, command, parameter))
        return {"statusCode": 100}


@pytest.mark.asyncio
async def test_sends_air_conditioner_set_all_command():
    client = FakeClient()
    service = RemoteControlService(client)

    result = await service.control_air_conditioner(
        "remote-1",
        AirConditionerControlRequest(
            temperature=26, mode="cool", fan_speed="medium", power="on"
        ),
    )

    assert client.commands == [("remote-1", "setAll", "26,2,3,on")]
    assert result.last_sent.temperature == 26


@pytest.mark.asyncio
async def test_rejects_non_air_conditioner_remote():
    service = RemoteControlService(FakeClient("TV"))

    with pytest.raises(LauncherError, match="エアコン操作に対応していません"):
        await service.control_air_conditioner(
            "remote-1",
            AirConditionerControlRequest(
                temperature=24, mode="auto", fan_speed="auto", power="off"
            ),
        )
