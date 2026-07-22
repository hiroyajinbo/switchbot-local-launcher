from __future__ import annotations

from typing import Any, Protocol

from app.credential_store import WindowsCredentialStore
from app.data_paths import load_desktop_settings, prepare_desktop_data
from app.errors import LauncherError
from app.main import create_app
from app.runtime import ManagedServer, configure_rotating_logging
from app.settings import Settings
from app.single_instance import SingleInstance, focus_window

WINDOW_TITLE = "SwitchBot Local Launcher"


class WebviewProtocol(Protocol):
    def create_window(self, title: str, url: str, **kwargs: Any) -> Any: ...

    def start(self, **kwargs: Any) -> None: ...


def run_desktop(
    *,
    settings: Settings | None = None,
    webview_module: WebviewProtocol | None = None,
    server_factory: type[ManagedServer] = ManagedServer,
    instance_factory: type[SingleInstance] = SingleInstance,
) -> None:
    instance = instance_factory()
    if not instance.acquire():
        focus_existing_window()
        return

    try:
        _run_desktop_window(
            settings=settings,
            webview_module=webview_module,
            server_factory=server_factory,
        )
    finally:
        instance.close()


def _run_desktop_window(
    *,
    settings: Settings | None,
    webview_module: WebviewProtocol | None,
    server_factory: type[ManagedServer],
) -> None:
    settings_loader = None
    credential_store = WindowsCredentialStore()
    if settings is None:
        try:
            paths = prepare_desktop_data()
            settings = load_desktop_settings(
                paths,
                credential_store=credential_store,
                allow_missing_credentials=True,
            )
            def settings_loader() -> Settings:
                return load_desktop_settings(
                    paths,
                    credential_store=credential_store,
                )
        except LauncherError as exc:
            print(f"ERROR: {exc}")
            raise SystemExit(1) from None

    if webview_module is None:
        try:
            import webview
        except ImportError:
            print(
                'ERROR: PCアプリ依存がありません。pip install -e ".[desktop]" '
                "を実行してください。"
            )
            raise SystemExit(1) from None
        webview_module = webview

    log_config = configure_rotating_logging(settings.log_path)
    server = server_factory(
        create_app(
            settings=settings,
            settings_loader=settings_loader,
            credential_store=credential_store,
        ),
        settings.host,
        settings.port,
        log_config=log_config,
    )
    try:
        url = server.start()
        window = webview_module.create_window(
            WINDOW_TITLE,
            url,
            width=1120,
            height=800,
            min_size=(720, 560),
        )
        window.events.closed += server.stop
        webview_module.start(gui="edgechromium", debug=False)
    except LauncherError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from None
    finally:
        server.stop()


def focus_existing_window() -> None:
    if not focus_window(WINDOW_TITLE):
        print("INFO: PCアプリは既に起動しています。既存ウィンドウを確認してください。")


def run() -> None:
    run_desktop()


if __name__ == "__main__":
    run()
