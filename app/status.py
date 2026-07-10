from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.errors import SwitchBotApiError
from app.switchbot_client import SwitchBotClient


@dataclass(frozen=True)
class DeviceStatusSnapshot:
    checked_at: str
    environment: list[dict[str, Any]]
    devices: list[dict[str, Any]]
    remotes: list[dict[str, Any]]
    errors: list[dict[str, str]]


class DeviceStatusService:
    def __init__(self, switchbot_client: SwitchBotClient) -> None:
        self._switchbot_client = switchbot_client

    async def snapshot(self) -> DeviceStatusSnapshot:
        devices_response = await self._switchbot_client.get_devices()
        devices_body = devices_response.get("body", {})
        devices = _collect_physical_devices(devices_body)
        remotes = _collect_infrared_remotes(devices_body)
        status_items = []
        errors = []

        for device in devices:
            device_id = device.get("deviceId")
            if not device_id:
                continue
            try:
                status_response = await self._switchbot_client.get_device_status(device_id)
            except SwitchBotApiError as exc:
                errors.append(
                    {
                        "device_id": device_id,
                        "label": device.get("deviceName") or device_id,
                        "message": str(exc),
                    }
                )
                continue
            body = status_response.get("body", {})
            status_items.append(_format_device_status(device, body))

        return DeviceStatusSnapshot(
            checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            environment=[item for item in status_items if item["kind"] == "environment"],
            devices=[item for item in status_items if item["kind"] != "environment"],
            remotes=[_format_remote(remote) for remote in remotes],
            errors=errors,
        )


def _collect_physical_devices(devices_body: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(device, source="deviceList")
        for device in devices_body.get("deviceList", [])
        if isinstance(device, dict)
    ]


def _collect_infrared_remotes(devices_body: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(device, source="infraredRemoteList")
        for device in devices_body.get("infraredRemoteList", [])
        if isinstance(device, dict)
    ]


def _format_device_status(device: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    device_type = (
        body.get("deviceType")
        or device.get("deviceType")
        or device.get("remoteType")
        or "Unknown"
    )
    status = {
        "device_id": device.get("deviceId"),
        "label": device.get("deviceName") or device.get("deviceId"),
        "type": device_type,
        "kind": "environment" if _has_environment_fields(body) else "device",
        "summary": _summary_for_status(body),
        "details": _details_for_status(body),
    }
    return status


def _format_remote(remote: dict[str, Any]) -> dict[str, Any]:
    remote_type = remote.get("remoteType") or "Infrared Remote"
    return {
        "device_id": remote.get("deviceId"),
        "label": remote.get("deviceName") or remote.get("deviceId"),
        "type": remote_type,
        "hub_device_id": remote.get("hubDeviceId"),
        "summary": "状態取得対象外。操作する場合はSwitchBotアプリでシーン化してください。",
    }


def _has_environment_fields(body: dict[str, Any]) -> bool:
    return any(key in body for key in ("temperature", "humidity", "lightLevel"))


def _summary_for_status(body: dict[str, Any]) -> str:
    if _has_environment_fields(body):
        parts = []
        if "temperature" in body:
            parts.append(f"{body['temperature']} C")
        if "humidity" in body:
            parts.append(f"{body['humidity']}%")
        if "lightLevel" in body:
            parts.append(f"light {body['lightLevel']}")
        return " / ".join(parts)

    if "power" in body:
        return f"power {body['power']}"
    if "lockState" in body:
        return f"lock {body['lockState']}"
    if "openState" in body:
        return f"open {body['openState']}"
    if body:
        return "status available"
    return "no status fields"


def _details_for_status(body: dict[str, Any]) -> list[dict[str, Any]]:
    detail_keys = [
        "power",
        "battery",
        "brightness",
        "colorTemperature",
        "temperature",
        "humidity",
        "lightLevel",
        "lockState",
        "doorState",
        "openState",
        "moveDetected",
        "deviceMode",
        "voltage",
        "electricCurrent",
        "electricityOfDay",
    ]
    return [{"key": key, "value": body[key]} for key in detail_keys if key in body]
