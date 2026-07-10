from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.actions import ActionExecutor, ActionResult
from app.config import load_config
from app.errors import ActionNotFoundError, LauncherError
from app.settings import Settings, load_settings
from app.status import DeviceStatusService, DeviceStatusSnapshot
from app.switchbot_client import SwitchBotClient, SwitchBotCredentials

WEB_DIR = Path(__file__).parent / "web"


def create_app(
    settings: Settings | None = None,
    executor: ActionExecutor | None = None,
    status_service: DeviceStatusService | None = None,
    startup_error: LauncherError | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if executor is not None or status_service is not None or startup_error is not None:
            app.state.executor = executor
            app.state.status_service = status_service
            app.state.startup_error = startup_error
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
            app.state.status_service = DeviceStatusService(switchbot_client)
            app.state.startup_error = None
        except LauncherError as exc:
            app.state.executor = None
            app.state.status_service = None
            app.state.startup_error = exc
        yield

    app = FastAPI(title="SwitchBot Local Launcher", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

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


app = create_app()


def run() -> None:
    try:
        settings = load_settings()
    except LauncherError:
        settings = Settings(switchbot_token="", switchbot_secret="")
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
