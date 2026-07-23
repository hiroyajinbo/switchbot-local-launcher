from typing import Literal

from pydantic import BaseModel, Field

from app.errors import LauncherError
from app.switchbot_client import SwitchBotClient


class AirConditionerControlRequest(BaseModel):
    temperature: int = Field(ge=16, le=30)
    mode: Literal["auto", "cool", "dry", "fan", "heat"]
    fan_speed: Literal["auto", "low", "medium", "high"]
    power: Literal["on", "off"]


class RemoteControlResult(BaseModel):
    success: bool = True
    message: str
    last_sent: AirConditionerControlRequest


_MODE_CODES = {"auto": 1, "cool": 2, "dry": 3, "fan": 4, "heat": 5}
_FAN_SPEED_CODES = {"auto": 1, "low": 2, "medium": 3, "high": 4}


class RemoteControlService:
    def __init__(self, client: SwitchBotClient, force_error: bool = False) -> None:
        self._client = client
        self._force_error = force_error

    async def control_air_conditioner(
        self, device_id: str, request: AirConditionerControlRequest
    ) -> RemoteControlResult:
        if self._force_error:
            raise LauncherError(
                "テスト用の操作失敗を発生させました。SwitchBotへは送信していません。"
            )
        remote_type, label = await self._find_remote(device_id)
        if remote_type not in {"Air Conditioner", "DIY Air Conditioner"}:
            raise LauncherError(f"{remote_type} はエアコン操作に対応していません。")

        parameter = ",".join(
            (
                str(request.temperature),
                str(_MODE_CODES[request.mode]),
                str(_FAN_SPEED_CODES[request.fan_speed]),
                request.power,
            )
        )
        await self._client.command_device(device_id, "setAll", parameter)
        power_label = "ON" if request.power == "on" else "OFF"
        return RemoteControlResult(
            message=f"{label} {request.temperature}℃ / {power_label} 送信成功",
            last_sent=request,
        )

    async def _find_remote(self, device_id: str) -> tuple[str, str]:
        body = (await self._client.get_devices()).get("body", {})
        remotes = body.get("infraredRemoteList", []) if isinstance(body, dict) else []
        for remote in remotes:
            if isinstance(remote, dict) and remote.get("deviceId") == device_id:
                remote_type = remote.get("remoteType") or "Infrared Remote"
                return remote_type, remote.get("deviceName") or device_id
        raise LauncherError("指定されたリモコンは現在のリモコン一覧にありません。")
