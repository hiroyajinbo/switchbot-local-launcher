import base64
import hashlib
import hmac
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from app.errors import SwitchBotApiError


@dataclass(frozen=True)
class SwitchBotCredentials:
    token: str
    secret: str


class SwitchBotClient:
    def __init__(
        self,
        credentials: SwitchBotCredentials,
        http_client: httpx.AsyncClient | None = None,
        base_url: str = "https://api.switch-bot.com/v1.1",
    ) -> None:
        self._credentials = credentials
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")

    async def command_device(
        self,
        device_id: str,
        command: str,
        parameter: str = "default",
        command_type: str = "command",
    ) -> dict[str, Any]:
        payload = {
            "command": command,
            "parameter": parameter,
            "commandType": command_type,
        }
        return await self._post(f"/devices/{device_id}/commands", payload)

    async def execute_scene(self, scene_id: str) -> dict[str, Any]:
        return await self._post(f"/scenes/{scene_id}/execute", {})

    async def get_devices(self) -> dict[str, Any]:
        return await self._get("/devices")

    async def get_device_status(self, device_id: str) -> dict[str, Any]:
        return await self._get(f"/devices/{device_id}/status")

    async def get_scenes(self) -> dict[str, Any]:
        return await self._get("/scenes")

    async def _get(self, path: str) -> dict[str, Any]:
        client = self._http_client
        if client is not None:
            return await self._request_with_client(client, "GET", path)

        async with httpx.AsyncClient(timeout=10.0) as owned_client:
            return await self._request_with_client(owned_client, "GET", path)

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        client = self._http_client
        if client is not None:
            return await self._request_with_client(client, "POST", path, payload)

        async with httpx.AsyncClient(timeout=10.0) as owned_client:
            return await self._request_with_client(owned_client, "POST", path, payload)

    async def _request_with_client(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            response = await client.request(method, url, json=payload, headers=self._headers())
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SwitchBotApiError(
                f"SwitchBot API returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise SwitchBotApiError(f"Could not connect to SwitchBot API: {exc}") from exc

        body = response.json()
        status_code = body.get("statusCode")
        if status_code not in (100, "100"):
            message = body.get("message") or "API error"
            raise SwitchBotApiError(f"SwitchBot API error: {status_code} {message}")
        return body

    def _headers(self) -> dict[str, str]:
        nonce = str(uuid.uuid4())
        timestamp = str(int(time.time() * 1000))
        string_to_sign = f"{self._credentials.token}{timestamp}{nonce}"
        digest = hmac.new(
            self._credentials.secret.encode("utf-8"),
            msg=string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = base64.b64encode(digest).decode("utf-8")
        return {
            "Authorization": self._credentials.token,
            "sign": sign,
            "nonce": nonce,
            "t": timestamp,
            "Content-Type": "application/json; charset=utf8",
        }
