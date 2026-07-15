from fastapi.testclient import TestClient

from app.actions import ActionResult
from app.config import LauncherConfig
from app.main import create_app
from app.status import DeviceStatusSnapshot


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


class FakeStatusService:
    async def snapshot(self):
        return DeviceStatusSnapshot(
            checked_at="2026-07-10 10:31:00",
            environment=[
                {
                    "device_id": "hub-1",
                    "label": "Hub 2",
                    "type": "Hub 2",
                    "kind": "environment",
                    "summary": "31.4 C / 58% / light 5",
                    "details": [{"key": "temperature", "value": 31.4}],
                }
            ],
            devices=[],
            remotes=[
                {
                    "device_id": "remote-1",
                    "label": "Air Conditioner",
                    "type": "Air Conditioner",
                    "hub_device_id": "hub-1",
                    "summary": "状態取得対象外。",
                }
            ],
            errors=[],
        )


def test_get_buttons():
    app = create_app(executor=FakeExecutor(), status_service=FakeStatusService())

    with TestClient(app) as client:
        response = client.get("/api/buttons")

    assert response.status_code == 200
    assert response.json()["buttons"] == [
        {
            "id": "light_on",
            "label": "照明 ON",
            "type": "device_command",
            "group": "その他",
            "locked": False,
        }
    ]


def test_index_disables_browser_cache():
    app = create_app(executor=FakeExecutor(), status_service=FakeStatusService())

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


def test_execute_action():
    app = create_app(executor=FakeExecutor(), status_service=FakeStatusService())

    with TestClient(app) as client:
        response = client.post("/api/actions/light_on")

    assert response.status_code == 200
    assert response.json()["message"] == "照明 ON 成功"


def test_get_status():
    app = create_app(executor=FakeExecutor(), status_service=FakeStatusService())

    with TestClient(app) as client:
        response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json()["environment"][0]["label"] == "Hub 2"
    assert response.json()["remotes"][0]["label"] == "Air Conditioner"
