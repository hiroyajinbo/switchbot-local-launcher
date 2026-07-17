from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.config import load_config
from app.errors import LauncherError
from app.switchbot_client import SwitchBotClient

POWER_DEVICE_TYPES = {"Ceiling Light", "Color Bulb", "Plug Mini (JP)", "Strip Light"}
BRIGHTNESS_DEVICE_TYPES = {"Ceiling Light", "Color Bulb", "Strip Light"}
COLOR_DEVICE_TYPES = {"Color Bulb", "Strip Light"}
COLOR_TEMPERATURE_DEVICE_TYPES = {"Ceiling Light", "Color Bulb"}


class DeviceControlRequest(BaseModel):
    action: Literal[
        "turn_on", "turn_off", "set_brightness", "set_color", "set_color_temperature", "press"
    ]
    value: int | str | None = None


class DeviceControlResult(BaseModel):
    success: bool = True
    message: str


class DeviceControlService:
    def __init__(
        self,
        client: SwitchBotClient,
        config_path: Path | None = None,
        force_error: bool = False,
    ) -> None:
        self._client = client
        self._config_path = config_path
        self._force_error = force_error

    async def execute(
        self, device_id: str, request: DeviceControlRequest
    ) -> DeviceControlResult:
        if self._force_error:
            raise LauncherError(
                "テスト用の操作失敗を発生させました。SwitchBotへは送信していません。"
            )
        if self._config_path is not None:
            preference = load_config(self._config_path).device_preferences.get(device_id)
            if preference is not None and preference.locked:
                raise LauncherError("このデバイスは操作ロックされています。")
        device_type, label = await self._find_device(device_id)
        if request.action == "press":
            if device_type != "Bot":
                raise LauncherError(f"{device_type} の押す操作には対応していません。")
            await self._client.command_device(device_id, "press")
            return DeviceControlResult(message=f"{label} 押す 成功")
        if request.action in {"turn_on", "turn_off"}:
            if device_type not in POWER_DEVICE_TYPES:
                raise LauncherError(f"{device_type} のON/OFF操作には対応していません。")
            command = "turnOn" if request.action == "turn_on" else "turnOff"
            await self._client.command_device(device_id, command)
            state = "ON" if command == "turnOn" else "OFF"
            return DeviceControlResult(message=f"{label} {state} 成功")

        if request.action == "set_color":
            if device_type not in COLOR_DEVICE_TYPES:
                raise LauncherError(f"{device_type} の色変更には対応していません。")
            color = str(request.value or "")
            parts = color.split(":")
            invalid_parts = any(
                not part.isdigit() or not 0 <= int(part) <= 255 for part in parts
            )
            if len(parts) != 3 or invalid_parts:
                raise LauncherError("色はRGB各0～255で指定してください。")
            await self._client.command_device(device_id, "setColor", color)
            return DeviceControlResult(message=f"{label} 色変更 成功")

        if request.action == "set_color_temperature":
            if device_type not in COLOR_TEMPERATURE_DEVICE_TYPES:
                raise LauncherError(f"{device_type} の色温度変更には対応していません。")
            try:
                temperature = int(request.value or 0)
            except (TypeError, ValueError) as exc:
                raise LauncherError("色温度を2700～6500Kで指定してください。") from exc
            if not 2700 <= temperature <= 6500:
                raise LauncherError("色温度を2700～6500Kで指定してください。")
            await self._client.command_device(device_id, "setColorTemperature", str(temperature))
            return DeviceControlResult(message=f"{label} 色温度 {temperature}K 成功")

        if device_type not in BRIGHTNESS_DEVICE_TYPES:
            raise LauncherError(f"{device_type} の明るさ変更には対応していません。")
        invalid_brightness = (
            request.value is None
            or not str(request.value).isdigit()
            or not 1 <= int(request.value) <= 100
        )
        if invalid_brightness:
            raise LauncherError("明るさを1～100で指定してください。")
        brightness = int(request.value)
        await self._client.command_device(device_id, "setBrightness", str(brightness))
        return DeviceControlResult(message=f"{label} 明るさ {brightness}% 成功")

    async def _find_device(self, device_id: str) -> tuple[str, str]:
        body = (await self._client.get_devices()).get("body", {})
        devices = body.get("deviceList", []) if isinstance(body, dict) else []
        for device in devices:
            if isinstance(device, dict) and device.get("deviceId") == device_id:
                device_type = device.get("deviceType") or "Unknown"
                return device_type, device.get("deviceName") or device_id
        raise LauncherError("指定されたデバイスは現在のデバイス一覧にありません。")
