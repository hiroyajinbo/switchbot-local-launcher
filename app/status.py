from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import DevicePreference, load_config
from app.device_control import (
    BRIGHTNESS_DEVICE_TYPES,
    COLOR_DEVICE_TYPES,
    COLOR_TEMPERATURE_DEVICE_TYPES,
    POWER_DEVICE_TYPES,
)
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
    def __init__(self, switchbot_client: SwitchBotClient, config_path: Path | None = None) -> None:
        self._switchbot_client = switchbot_client
        self._config_path = config_path
        self._last_status_items: dict[str, dict[str, Any]] = {}

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
                cached = self._last_status_items.get(device_id)
                if cached is not None:
                    status_items.append(dict(cached, stale=True, status_error=str(exc)))
                continue
            body = status_response.get("body", {})
            item = _format_device_status(device, body, self._preference(device, body))
            if self._config_path is not None:
                presets = load_config(self._config_path).light_presets.get(device_id, [])
                item["presets"] = [preset.model_dump() for preset in presets]
            status_items.append(item)
            self._last_status_items[device_id] = item

        return DeviceStatusSnapshot(
            checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            environment=[item for item in status_items if item["kind"] == "environment"],
            devices=[item for item in status_items if item["kind"] != "environment"],
            remotes=[_format_remote(remote) for remote in remotes],
            errors=errors,
        )

    def _preference(self, device: dict[str, Any], body: dict[str, Any]) -> DevicePreference:
        device_id = device.get("deviceId")
        if self._config_path is not None and device_id:
            saved = load_config(self._config_path).device_preferences.get(device_id)
            if saved is not None:
                return saved
        device_type = body.get("deviceType") or device.get("deviceType") or "Unknown"
        return DevicePreference(icon=_default_icon(device_type))


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


def _format_device_status(
    device: dict[str, Any], body: dict[str, Any], preference: DevicePreference | None = None
) -> dict[str, Any]:
    device_type = (
        body.get("deviceType")
        or device.get("deviceType")
        or device.get("remoteType")
        or "Unknown"
    )
    preference = preference or DevicePreference(icon=_default_icon(device_type))
    status = {
        "device_id": device.get("deviceId"),
        "label": device.get("deviceName") or device.get("deviceId"),
        "type": device_type,
        "kind": "environment" if _has_environment_fields(body) else "device",
        "summary": _summary_for_status(body),
        "details": _details_for_status(body),
        "controls": {
            "power": device_type in POWER_DEVICE_TYPES,
            "brightness": device_type in BRIGHTNESS_DEVICE_TYPES,
            "press": device_type == "Bot" and body.get("deviceMode") == "pressMode",
            "color": device_type in COLOR_DEVICE_TYPES,
            "color_temperature": device_type in COLOR_TEMPERATURE_DEVICE_TYPES,
        },
        "room": preference.room,
        "icon": preference.icon,
        "locked": preference.locked,
        "presets": [],
    }
    return status


def _default_icon(device_type: str) -> str:
    if device_type == "Strip Light":
        return "strip_light"
    if device_type in BRIGHTNESS_DEVICE_TYPES:
        return "light"
    if device_type == "Plug Mini (JP)":
        return "plug"
    if device_type in {"Contact Sensor"}:
        return "sensor"
    if device_type == "Smart Lock":
        return "lock"
    if device_type.startswith("Hub"):
        return "hub"
    if device_type == "Bot":
        return "bot"
    return "other"


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
        "color",
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
