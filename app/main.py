from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.actions import ActionExecutor, ActionResult
from app.config import load_config
from app.config_sync import (
    ApplyCandidatesRequest,
    ApplyCandidatesResult,
    ButtonAppearanceUpdate,
    ConfigCandidateList,
    ConfigSyncService,
)
from app.desktop_integration import DesktopIntegration
from app.device_control import DeviceControlRequest, DeviceControlResult, DeviceControlService
from app.device_preferences import (
    DevicePreferenceService,
    DevicePreferenceUpdate,
    LightPresetUpdate,
    RoomOrderUpdate,
)
from app.errors import ActionNotFoundError, LauncherError
from app.remote_control import (
    AirConditionerControlRequest,
    RemoteControlResult,
    RemoteControlService,
)
from app.runtime import ManagedServer, configure_rotating_logging
from app.settings import Settings, load_settings
from app.status import DeviceStatusService, DeviceStatusSnapshot
from app.switchbot_client import SwitchBotClient, SwitchBotCredentials

WEB_DIR = Path(__file__).parent / "web"


def create_app(
    settings: Settings | None = None,
    executor: ActionExecutor | None = None,
    status_service: DeviceStatusService | None = None,
    startup_error: LauncherError | None = None,
    config_sync_service: ConfigSyncService | None = None,
    device_control_service: DeviceControlService | None = None,
    device_preference_service: DevicePreferenceService | None = None,
    desktop_integration: DesktopIntegration | None = None,
    remote_control_service: RemoteControlService | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if executor is not None or status_service is not None or startup_error is not None:
            app.state.executor = executor
            app.state.status_service = status_service
            app.state.startup_error = startup_error
            app.state.config_sync_service = config_sync_service
            app.state.device_control_service = device_control_service
            app.state.device_preference_service = device_preference_service
            app.state.desktop_integration = desktop_integration
            app.state.remote_control_service = remote_control_service
            yield
            return

        try:
            loaded_settings = settings or load_settings()
            config = load_config(loaded_settings.config_path)
            credentials = SwitchBotCredentials(
                token=loaded_settings.switchbot_token,
                secret=loaded_settings.switchbot_secret,
            )
            switchbot_client = SwitchBotClient(credentials)
            app.state.executor = ActionExecutor(config, switchbot_client)
            app.state.config_sync_service = ConfigSyncService(
                Path(loaded_settings.config_path), switchbot_client
            )
            config_path = Path(loaded_settings.config_path)
            app.state.status_service = DeviceStatusService(switchbot_client, config_path)
            app.state.device_control_service = DeviceControlService(
                switchbot_client,
                config_path,
                force_error=loaded_settings.force_control_error,
            )
            app.state.remote_control_service = RemoteControlService(
                switchbot_client, force_error=loaded_settings.force_control_error
            )
            app.state.device_preference_service = DevicePreferenceService(config_path)
            app.state.desktop_integration = DesktopIntegration(loaded_settings.log_path)
            app.state.startup_error = None
        except LauncherError as exc:
            app.state.executor = None
            app.state.status_service = None
            app.state.startup_error = exc
        yield

    app = FastAPI(title="SwitchBot Local Launcher", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.middleware("http")
    async def disable_local_cache(request: Request, call_next) -> Response:
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        error = getattr(app.state, "startup_error", None)
        return {"ok": error is None, "error": str(error) if error else None}

    @app.get("/api/buttons")
    async def buttons() -> dict[str, Any]:
        current_executor = _get_executor(app)
        return {
            "buttons": [
                {
                    "id": button.id,
                    "label": button.label,
                    "type": button.type,
                    "group": button.group,
                    "locked": button.locked,
                    "icon": button.icon,
                    "icon_badge": button.icon_badge,
                }
                for button in current_executor.buttons
            ]
        }

    @app.post("/api/actions/{button_id}")
    async def execute_action(button_id: str) -> ActionResult:
        current_executor = _get_executor(app)
        try:
            return await current_executor.execute(button_id)
        except ActionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except LauncherError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get("/api/status")
    async def device_status() -> DeviceStatusSnapshot:
        current_status_service = _get_status_service(app)
        try:
            return await current_status_service.snapshot()
        except LauncherError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/api/config/candidates")
    async def config_candidates() -> ConfigCandidateList:
        service = _get_config_sync_service(app)
        try:
            return await service.refresh()
        except LauncherError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/api/config/apply")
    async def apply_config_candidates(request: ApplyCandidatesRequest) -> ApplyCandidatesResult:
        service = _get_config_sync_service(app)
        try:
            result = service.apply(request.ids)
            _get_executor(app).replace_config(service.current_config())
            return result
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/config/remove")
    async def remove_config_buttons(request: ApplyCandidatesRequest) -> dict[str, int]:
        service = _get_config_sync_service(app)
        try:
            result = service.remove_buttons(request.ids)
            _get_executor(app).replace_config(service.current_config())
            return result
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/buttons/{button_id}/lock")
    async def update_button_lock(button_id: str, payload: dict[str, bool]) -> dict[str, Any]:
        service = _get_config_sync_service(app)
        try:
            locked = payload.get("locked", False)
            result = service.set_button_lock(button_id, locked)
            _get_executor(app).set_lock(button_id, locked)
            return result
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/devices/{device_id}/control")
    async def control_device(
        device_id: str, request: DeviceControlRequest
    ) -> DeviceControlResult:
        service = _get_device_control_service(app)
        try:
            return await service.execute(device_id, request)
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/devices/{device_id}/preference")
    async def update_device_preference(
        device_id: str, update: DevicePreferenceUpdate
    ) -> dict[str, Any]:
        service = getattr(app.state, "device_preference_service", None)
        if service is None:
            raise HTTPException(
                status_code=500, detail="デバイス設定サービスが初期化されていません。"
            )
        try:
            return service.update(device_id, update).model_dump()
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/devices/{device_id}/presets")
    async def add_light_preset(device_id: str, update: LightPresetUpdate) -> dict[str, Any]:
        service = getattr(app.state, "device_preference_service", None)
        if service is None:
            raise HTTPException(
                status_code=500, detail="プリセットサービスが初期化されていません。"
            )
        return service.add_preset(device_id, update).model_dump()

    @app.delete("/api/devices/{device_id}/presets/{preset_name}")
    async def remove_light_preset(device_id: str, preset_name: str) -> dict[str, Any]:
        service = getattr(app.state, "device_preference_service", None)
        if service is None:
            raise HTTPException(
                status_code=500, detail="プリセットサービスが初期化されていません。"
            )
        if not service.remove_preset(device_id, preset_name):
            raise HTTPException(status_code=404, detail="マイセットが見つかりません。")
        return {"removed": True, "name": preset_name}

    @app.put("/api/devices/{device_id}/presets/{preset_name}")
    async def update_light_preset(
        device_id: str, preset_name: str, update: LightPresetUpdate
    ) -> dict[str, Any]:
        service = getattr(app.state, "device_preference_service", None)
        if service is None:
            raise HTTPException(
                status_code=500, detail="プリセットサービスが初期化されていません。"
            )
        try:
            return service.update_preset(device_id, preset_name, update).model_dump()
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/rooms")
    async def get_rooms() -> dict[str, Any]:
        service = getattr(app.state, "device_preference_service", None)
        if service is None:
            raise HTTPException(status_code=500, detail="部屋設定サービスが初期化されていません。")
        return {"rooms": service.rooms()}

    @app.post("/api/rooms")
    async def add_room(payload: dict[str, str]) -> dict[str, Any]:
        service = getattr(app.state, "device_preference_service", None)
        if service is None:
            raise HTTPException(status_code=500, detail="部屋設定サービスが初期化されていません。")
        return {"rooms": service.add_room(payload.get("room", ""))}

    @app.put("/api/rooms/order")
    async def reorder_rooms(update: RoomOrderUpdate) -> dict[str, Any]:
        service = getattr(app.state, "device_preference_service", None)
        if service is None:
            raise HTTPException(status_code=500, detail="部屋設定サービスが初期化されていません。")
        try:
            return {"rooms": service.reorder_rooms(update.rooms)}
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/remotes/{device_id}/air-conditioner")
    async def control_air_conditioner(
        device_id: str, request: AirConditionerControlRequest
    ) -> RemoteControlResult:
        service = _get_remote_control_service(app)
        try:
            return await service.control_air_conditioner(device_id, request)
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/buttons/{button_id}/appearance")
    async def update_button_appearance(
        button_id: str, update: ButtonAppearanceUpdate
    ) -> dict[str, Any]:
        service = _get_config_sync_service(app)
        try:
            result = service.set_button_appearance(button_id, update)
            _get_executor(app).replace_config(service.current_config())
            return result
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/rooms/{room}")
    async def remove_room(room: str) -> dict[str, Any]:
        service = getattr(app.state, "device_preference_service", None)
        if service is None:
            raise HTTPException(status_code=500, detail="部屋設定サービスが初期化されていません。")
        try:
            return service.remove_room(room)
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/desktop")
    async def desktop_status() -> dict[str, Any]:
        return _get_desktop_integration(app).status()

    @app.put("/api/desktop/autostart")
    async def update_desktop_autostart(payload: dict[str, bool]) -> dict[str, Any]:
        service = _get_desktop_integration(app)
        try:
            enabled = service.set_autostart(payload.get("enabled", False))
            return {"autostart_enabled": enabled}
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/desktop/open-logs")
    async def open_desktop_logs() -> dict[str, str]:
        service = _get_desktop_integration(app)
        try:
            return {"log_directory": service.open_log_directory()}
        except LauncherError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


def _get_executor(app: FastAPI) -> ActionExecutor:
    startup_error = getattr(app.state, "startup_error", None)
    if startup_error is not None:
        raise HTTPException(status_code=500, detail=str(startup_error))

    executor = getattr(app.state, "executor", None)
    if executor is None:
        raise HTTPException(status_code=500, detail="アプリが初期化されていません。")
    return executor


def _get_status_service(app: FastAPI) -> DeviceStatusService:
    startup_error = getattr(app.state, "startup_error", None)
    if startup_error is not None:
        raise HTTPException(status_code=500, detail=str(startup_error))

    status_service = getattr(app.state, "status_service", None)
    if status_service is None:
        raise HTTPException(status_code=500, detail="状態取得サービスが初期化されていません。")
    return status_service


def _get_config_sync_service(app: FastAPI) -> ConfigSyncService:
    service = getattr(app.state, "config_sync_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="設定更新サービスが初期化されていません。")
    return service


def _get_device_control_service(app: FastAPI) -> DeviceControlService:
    service = getattr(app.state, "device_control_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="デバイス操作サービスが初期化されていません。")
    return service


def _get_desktop_integration(app: FastAPI) -> DesktopIntegration:
    service = getattr(app.state, "desktop_integration", None)
    if service is None:
        raise HTTPException(status_code=500, detail="PCアプリ連携が初期化されていません。")
    return service


def _get_remote_control_service(app: FastAPI) -> RemoteControlService:
    service = getattr(app.state, "remote_control_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="リモコン操作サービスが初期化されていません。")
    return service


app = create_app()


def run() -> None:
    try:
        settings = load_settings()
    except LauncherError:
        settings = Settings(switchbot_token="", switchbot_secret="")
    log_config = configure_rotating_logging(settings.log_path)
    server = ManagedServer(
        "app.main:app",
        settings.host,
        settings.port,
        log_config=log_config,
    )
    try:
        server.start()
        server.wait()
    except KeyboardInterrupt:
        pass
    except LauncherError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from None
    finally:
        server.stop()
