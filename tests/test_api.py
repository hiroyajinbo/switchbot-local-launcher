import json

from fastapi.testclient import TestClient

from app.actions import ActionResult
from app.config import LauncherConfig, load_config
from app.config_sync import ConfigSyncService
from app.credential_store import StoredCredentials
from app.device_preferences import DevicePreferenceService
from app.errors import SecretConfigError, SwitchBotApiError
from app.main import create_app
from app.settings import Settings
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

    def replace_config(self, config):
        self.config = config
        self.buttons = config.buttons


class FakeDiscoveryClient:
    async def get_devices(self):
        return {"body": {"deviceList": [], "infraredRemoteList": []}}

    async def get_scenes(self):
        return {"body": [{"sceneId": "scene-1", "sceneName": "帰宅"}]}


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


class FakeRemoteControlService:
    async def control_air_conditioner(self, device_id, request):
        return {
            "success": True,
            "message": f"{device_id} {request.temperature}℃ 送信成功",
            "last_sent": request.model_dump(),
        }


class FakeCredentialStore:
    available = True

    def __init__(self) -> None:
        self.credentials = None

    def load(self):
        return self.credentials

    def save(self, credentials) -> None:
        self.credentials = credentials


class FakeSwitchBotClient:
    should_fail = False

    def __init__(self, credentials) -> None:
        self.credentials = credentials

    async def get_devices(self):
        if self.should_fail:
            raise SwitchBotApiError("invalid credentials")
        return {"statusCode": 100, "body": {"deviceList": []}}


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


def test_scene_auto_add_refreshes_buttons_endpoint(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [],
                "scene_sync": {"auto_add": True, "excluded_scene_ids": []},
            }
        ),
        encoding="utf-8",
    )
    executor = FakeExecutor()
    sync_service = ConfigSyncService(config_path, FakeDiscoveryClient())
    app = create_app(
        executor=executor,
        status_service=FakeStatusService(),
        config_sync_service=sync_service,
    )

    with TestClient(app) as client:
        candidates = client.post("/api/config/candidates")
        buttons = client.get("/api/buttons")

    assert candidates.status_code == 200
    assert candidates.json()["auto_added"] == 1
    assert [button["label"] for button in buttons.json()["buttons"]] == ["帰宅"]


def test_scene_delete_exclusion_restore_and_setting_endpoints(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {
                        "id": "scene_home",
                        "label": "帰宅",
                        "type": "scene",
                        "scene_id": "scene-1",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    executor = FakeExecutor()
    sync_service = ConfigSyncService(config_path, FakeDiscoveryClient())
    app = create_app(
        executor=executor,
        status_service=FakeStatusService(),
        config_sync_service=sync_service,
    )

    with TestClient(app) as client:
        removed = client.delete("/api/config/scenes/scene_home")
        after_remove = client.post("/api/config/candidates")
        restored = client.delete("/api/config/scenes/exclusions/scene-1")
        after_restore = client.post("/api/config/candidates")
        setting = client.put("/api/config/scenes/settings", json={"auto_add": True})

    assert removed.status_code == 200
    assert after_remove.json()["excluded_scenes"][0]["source_id"] == "scene-1"
    assert restored.json() == {"scene_id": "scene-1", "excluded": False}
    assert [item["source_id"] for item in after_restore.json()["candidates"]] == [
        "scene-1"
    ]
    assert setting.json() == {"auto_add": True}
    assert load_config(config_path).scene_sync.auto_add is True


def test_quick_action_group_endpoints_add_reorder_and_remove(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "quick_action_groups": ["シーン", "空調"],
                "buttons": [
                    {
                        "id": "scene_home",
                        "label": "帰宅",
                        "group": "空調",
                        "type": "scene",
                        "scene_id": "scene-1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    executor = FakeExecutor()
    sync_service = ConfigSyncService(config_path, FakeDiscoveryClient())
    app = create_app(
        executor=executor,
        status_service=FakeStatusService(),
        config_sync_service=sync_service,
    )

    with TestClient(app) as client:
        initial = client.get("/api/quick-action-groups")
        added = client.post("/api/quick-action-groups", json={"group": "モニター"})
        reordered = client.put(
            "/api/quick-action-groups/order",
            json={"groups": ["モニター", "シーン", "空調"]},
        )
        removed = client.delete("/api/quick-action-groups/空調")

    assert initial.json() == {"groups": ["シーン", "空調"]}
    assert added.json() == {"groups": ["シーン", "空調", "モニター"]}
    assert reordered.json() == {"groups": ["モニター", "シーン", "空調"]}
    assert removed.json()["moved_buttons"] == 1
    assert removed.json()["groups"] == ["モニター", "シーン"]
    assert executor.config.get_button("scene_home").group == "シーン"


def test_initial_setup_saves_verified_credentials_and_initializes_app(
    tmp_path, monkeypatch
):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [
                    {"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}
                ]
            }
        ),
        encoding="utf-8",
    )
    store = FakeCredentialStore()
    bootstrap = Settings(
        switchbot_token="",
        switchbot_secret="",
        config_path=str(config_path),
        credentials_source="missing",
    )

    def settings_loader():
        credentials = store.load()
        if credentials is None:
            raise SecretConfigError("初回設定してください。")
        return Settings(
            switchbot_token=credentials.token,
            switchbot_secret=credentials.secret,
            config_path=str(config_path),
            credentials_source="windows",
        )

    FakeSwitchBotClient.should_fail = False
    monkeypatch.setattr("app.main.SwitchBotClient", FakeSwitchBotClient)
    app = create_app(
        settings=bootstrap,
        settings_loader=settings_loader,
        credential_store=store,
    )

    with TestClient(app) as client:
        before = client.get("/api/setup/status")
        saved = client.post(
            "/api/setup/credentials",
            json={"token": "new-token", "secret": "new-secret"},
        )
        health = client.get("/api/health")
        after = client.get("/api/setup/status")

    assert before.json()["required"] is True
    assert saved.status_code == 200, saved.text
    assert saved.json()["source"] == "windows"
    assert store.credentials == StoredCredentials(token="new-token", secret="new-secret")
    assert health.json()["ok"] is True
    assert after.json()["required"] is False


def test_initial_setup_does_not_save_invalid_credentials(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"buttons": []}', encoding="utf-8")
    store = FakeCredentialStore()
    bootstrap = Settings(
        switchbot_token="",
        switchbot_secret="",
        config_path=str(config_path),
        credentials_source="missing",
    )

    def settings_loader():
        raise SecretConfigError("初回設定してください。")

    FakeSwitchBotClient.should_fail = True
    monkeypatch.setattr("app.main.SwitchBotClient", FakeSwitchBotClient)
    app = create_app(
        settings=bootstrap,
        settings_loader=settings_loader,
        credential_store=store,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/setup/credentials",
            json={"token": "wrong", "secret": "wrong"},
        )
        status = client.get("/api/setup/status")

    assert response.status_code == 400
    assert "認証を確認できませんでした" in response.json()["detail"]
    assert store.credentials is None
    assert status.json()["required"] is True


def test_existing_credentials_can_be_replaced_after_verification(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"buttons": []}', encoding="utf-8")
    store = FakeCredentialStore()
    store.credentials = StoredCredentials(token="old-token", secret="old-secret")

    def settings_loader():
        credentials = store.load()
        return Settings(
            switchbot_token=credentials.token,
            switchbot_secret=credentials.secret,
            config_path=str(config_path),
            credentials_source="windows",
        )

    monkeypatch.setattr(FakeSwitchBotClient, "should_fail", False)
    monkeypatch.setattr("app.main.SwitchBotClient", FakeSwitchBotClient)
    app = create_app(
        settings_loader=settings_loader,
        credential_store=store,
    )

    with TestClient(app) as client:
        before = client.get("/api/setup/status")
        updated = client.put(
            "/api/setup/credentials",
            json={"token": "new-token", "secret": "new-secret"},
        )
        health = client.get("/api/health")

    assert before.json()["can_update"] is True
    assert updated.status_code == 200, updated.text
    assert updated.json()["source"] == "windows"
    assert store.credentials == StoredCredentials(token="new-token", secret="new-secret")
    assert health.json()["ok"] is True


def test_invalid_replacement_keeps_existing_credentials(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"buttons": []}', encoding="utf-8")
    store = FakeCredentialStore()
    original = StoredCredentials(token="old-token", secret="old-secret")
    store.credentials = original

    def settings_loader():
        credentials = store.load()
        return Settings(
            switchbot_token=credentials.token,
            switchbot_secret=credentials.secret,
            config_path=str(config_path),
            credentials_source="windows",
        )

    monkeypatch.setattr(FakeSwitchBotClient, "should_fail", False)
    monkeypatch.setattr("app.main.SwitchBotClient", FakeSwitchBotClient)
    app = create_app(
        settings_loader=settings_loader,
        credential_store=store,
    )

    with TestClient(app) as client:
        FakeSwitchBotClient.should_fail = True
        response = client.put(
            "/api/setup/credentials",
            json={"token": "wrong", "secret": "wrong"},
        )

    assert response.status_code == 400
    assert "認証を確認できませんでした" in response.json()["detail"]
    assert store.credentials == original


def test_env_credentials_must_be_updated_in_env_file() -> None:
    store = FakeCredentialStore()
    settings = Settings(
        switchbot_token="env-token",
        switchbot_secret="env-secret",
        credentials_source="env",
    )
    app = create_app(
        settings=settings,
        executor=FakeExecutor(),
        status_service=FakeStatusService(),
        credential_store=store,
    )

    with TestClient(app) as client:
        status = client.get("/api/setup/status")
        response = client.put(
            "/api/setup/credentials",
            json={"token": "new-token", "secret": "new-secret"},
        )

    assert status.json()["can_update"] is False
    assert response.status_code == 409
    assert ".env" in response.json()["detail"]
    assert store.credentials is None


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


def test_control_air_conditioner():
    app = create_app(
        executor=FakeExecutor(),
        status_service=FakeStatusService(),
        remote_control_service=FakeRemoteControlService(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/remotes/remote-1/air-conditioner",
            json={
                "temperature": 25,
                "mode": "cool",
                "fan_speed": "auto",
                "power": "on",
            },
        )

    assert response.status_code == 200
    assert response.json()["last_sent"]["mode"] == "cool"




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


def test_device_exclusion_endpoints_hide_and_restore_without_deleting_preferences(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "buttons": [{"id": "scene", "label": "Scene", "type": "scene", "scene_id": "1"}],
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
        before = client.get("/api/device-exclusions")
        hidden = client.post(
            "/api/devices/light-1/exclusion",
            json={"label": "寝室照明"},
        )
        restored = client.delete("/api/devices/light-1/exclusion")

    assert before.json() == {"devices": []}
    assert hidden.json()["devices"] == [
        {"device_id": "light-1", "label": "寝室照明"}
    ]
    assert restored.json()["devices"] == []
    saved = load_config(config_path)
    assert saved.device_preferences["light-1"].room == "寝室"
    assert saved.excluded_devices == {}
