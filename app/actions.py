from dataclasses import dataclass
from datetime import datetime

from app.config import Button, DeviceCommandButton, LauncherConfig, SceneButton
from app.errors import ActionNotFoundError
from app.switchbot_client import SwitchBotClient


@dataclass(frozen=True)
class ActionResult:
    button_id: str
    label: str
    success: bool
    message: str
    executed_at: str


class ActionExecutor:
    def __init__(self, config: LauncherConfig, switchbot_client: SwitchBotClient) -> None:
        self._config = config
        self._switchbot_client = switchbot_client

    @property
    def buttons(self) -> list[Button]:
        return self._config.buttons

    async def execute(self, button_id: str) -> ActionResult:
        button = self._config.get_button(button_id)
        if button is None:
            raise ActionNotFoundError(f"未定義のボタンIDです: {button_id}")

        if isinstance(button, DeviceCommandButton):
            await self._switchbot_client.command_device(
                device_id=button.device_id,
                command=button.command,
                parameter=button.parameter,
                command_type=button.command_type,
            )
        elif isinstance(button, SceneButton):
            await self._switchbot_client.execute_scene(button.scene_id)

        return ActionResult(
            button_id=button.id,
            label=button.label,
            success=True,
            message=f"{button.label} 成功",
            executed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
