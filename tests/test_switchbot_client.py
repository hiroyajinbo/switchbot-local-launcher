import httpx
import pytest

from app.errors import SwitchBotApiError
from app.switchbot_client import SwitchBotClient, SwitchBotCredentials


@pytest.mark.asyncio
async def test_command_device_sends_signed_request():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"statusCode": 100, "message": "success"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SwitchBotClient(
            SwitchBotCredentials(token="token", secret="secret"),
            http_client=http_client,
            base_url="https://example.test/v1.1",
        )

        result = await client.command_device("device-1", "turnOn")

    assert result["statusCode"] == 100
    assert requests[0].url.path == "/v1.1/devices/device-1/commands"
    assert requests[0].headers["Authorization"] == "token"
    assert requests[0].headers["sign"]
    assert requests[0].headers["nonce"]
    assert requests[0].headers["t"]


@pytest.mark.asyncio
async def test_command_device_raises_on_api_error():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"statusCode": 190, "message": "invalid"})
    )
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SwitchBotClient(
            SwitchBotCredentials(token="token", secret="secret"),
            http_client=http_client,
            base_url="https://example.test/v1.1",
        )

        with pytest.raises(SwitchBotApiError, match="190"):
            await client.command_device("device-1", "turnOn")


@pytest.mark.asyncio
async def test_get_devices_uses_devices_endpoint():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"statusCode": 100, "body": {"deviceList": []}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SwitchBotClient(
            SwitchBotCredentials(token="token", secret="secret"),
            http_client=http_client,
            base_url="https://example.test/v1.1",
        )

        result = await client.get_devices()

    assert result["body"] == {"deviceList": []}
    assert requests[0].method == "GET"
    assert requests[0].url.path == "/v1.1/devices"
