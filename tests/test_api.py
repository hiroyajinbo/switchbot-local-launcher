from fastapi.testclient import TestClient

from app.actions import ActionResult
from app.config import LauncherConfig
from app.main import create_app


class FakeExecutor:
    def __init__(self):
        self.config = LauncherConfig.model_validate(
            {
                "buttons": [
                    {
                        "id": "light_on",
                        "label": "照明 ON",
                        "type": "device_command",
                        "device_id": "device-1",
                        "command": "turnOn",
                    }
                ]
            }
        )
        self.buttons = self.config.buttons

    async def execute(self, button_id):
        return ActionResult(
            button_id=button_id,
            label="照明 ON",
            success=True,
            message="照明 ON 成功",
            executed_at="2026-07-10 10:30:00",
        )


def test_get_buttons():
    app = create_app(executor=FakeExecutor())

    with TestClient(app) as client:
        response = client.get("/api/buttons")

    assert response.status_code == 200
    assert response.json()["buttons"] == [
        {"id": "light_on", "label": "照明 ON", "type": "device_command"}
    ]


def test_execute_action():
    app = create_app(executor=FakeExecutor())

    with TestClient(app) as client:
        response = client.post("/api/actions/light_on")

    assert response.status_code == 200
    assert response.json()["message"] == "照明 ON 成功"
