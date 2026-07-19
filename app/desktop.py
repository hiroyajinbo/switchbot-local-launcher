from __future__ import annotations

from typing import Any, Protocol

from app.errors import LauncherError
from app.runtime import ManagedServer, configure_rotating_logging
from app.settings import Settings, load_settings
from app.single_instance import SingleInstance

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
    if settings is None:
        try:
            settings = load_settings()
        except LauncherError:
            settings = Settings(switchbot_token="", switchbot_secret="")

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
        "app.main:app",
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
    try:
        from pywinauto import Desktop

        window = Desktop(backend="uia").window(title=WINDOW_TITLE)
        window.wait("visible", timeout=5)
        window.restore()
        window.set_focus()
    except Exception as exc:  # GUI backends expose several platform-specific exceptions.
        print(f"INFO: PCアプリは既に起動しています。既存ウィンドウを確認してください: {exc}")


def run() -> None:
    run_desktop()


if __name__ == "__main__":
    run()
