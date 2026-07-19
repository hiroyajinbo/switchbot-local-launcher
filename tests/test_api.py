import json

from fastapi.testclient import TestClient

from app.actions import ActionResult
from app.config import LauncherConfig
from app.device_preferences import DevicePreferenceService
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


class FakeDesktopIntegration:
    def __init__(self):
        self.enabled = False
        self.opened = False

    def status(self):
        return {
            "available": True,
            "autostart_enabled": self.enabled,
            "log_directory": "C:\\Logs",
        }

    def set_autostart(self, enabled):
        self.enabled = enabled
        return enabled

    def open_log_directory(self):
        self.opened = True
        return "C:\\Logs"


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
            "icon": "other",
            "icon_badge": "none",
        }
    ]


def test_desktop_settings_endpoints():
    desktop = FakeDesktopIntegration()
    app = create_app(
        executor=FakeExecutor(),
        status_service=FakeStatusService(),
        desktop_integration=desktop,
    )

    with TestClient(app) as client:
        status = client.get("/api/desktop")
        enabled = client.put("/api/desktop/autostart", json={"enabled": True})
        logs = client.post("/api/desktop/open-logs")

    assert status.status_code == 200
    assert status.json()["autostart_enabled"] is False
    assert enabled.json() == {"autostart_enabled": True}
    assert logs.json() == {"log_directory": "C:\\Logs"}
    assert desktop.opened is True


def test_index_disables_browser_cache():
    app = create_app(executor=FakeExecutor(), status_service=FakeStatusService())

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.text.index('class="scene-panel"') < response.text.index(
        'class="device-panel primary-panel"'
    )


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




def test_remove_room_moves_devices_to_uncategorized(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
                "rooms": ["未分類", "寝室"],
                "device_preferences": {
                    "light-1": {"room": "寝室", "icon": "light", "locked": True}
                },
            }
        ),
        encoding="utf-8",
    )
    app = create_app(
        executor=FakeExecutor(),
        status_service=FakeStatusService(),
        device_preference_service=DevicePreferenceService(config_path),
    )

    with TestClient(app) as client:
        response = client.delete("/api/rooms/寝室")

    assert response.status_code == 200
    assert response.json()["moved_devices"] == 1
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["device_preferences"]["light-1"]["room"] == "未分類"


def test_remove_room_refuses_uncategorized_room(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {"buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}]}
        ),
        encoding="utf-8",
    )
    app = create_app(
        executor=FakeExecutor(),
        status_service=FakeStatusService(),
        device_preference_service=DevicePreferenceService(config_path),
    )

    with TestClient(app) as client:
        response = client.delete("/api/rooms/未分類")

    assert response.status_code == 400
    assert "削除できません" in response.json()["detail"]
