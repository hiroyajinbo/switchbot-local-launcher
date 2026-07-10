import pytest

from app.status import DeviceStatusService


class FakeSwitchBotClient:
    async def get_devices(self):
        return {
            "statusCode": 100,
            "body": {
                "deviceList": [
                    {"deviceId": "hub-1", "deviceName": "Hub 2", "deviceType": "Hub 2"},
                    {"deviceId": "light-1", "deviceName": "Light", "deviceType": "Color Bulb"},
                ],
                "infraredRemoteList": [
                    {
                        "deviceId": "remote-1",
                        "deviceName": "Air Conditioner",
                        "remoteType": "Air Conditioner",
                        "hubDeviceId": "hub-1",
                    }
                ],
            },
        }

    async def get_device_status(self, device_id):
        if device_id == "hub-1":
            return {
                "statusCode": 100,
                "body": {
                    "deviceId": device_id,
                    "deviceType": "Hub 2",
                    "temperature": 31.4,
                    "humidity": 58,
                    "lightLevel": 5,
                },
            }
        return {
            "statusCode": 100,
            "body": {
                "deviceId": device_id,
                "deviceType": "Color Bulb",
                "power": "on",
                "brightness": 50,
            },
        }


@pytest.mark.asyncio
async def test_status_snapshot_splits_environment_and_devices():
    service = DeviceStatusService(FakeSwitchBotClient())

    snapshot = await service.snapshot()

    assert snapshot.environment[0]["label"] == "Hub 2"
    assert snapshot.environment[0]["summary"] == "31.4 C / 58% / light 5"
    assert snapshot.devices[0]["label"] == "Light"
    assert snapshot.devices[0]["summary"] == "power on"
    assert snapshot.remotes[0]["label"] == "Air Conditioner"
    assert snapshot.remotes[0]["summary"].startswith("状態取得対象外")
