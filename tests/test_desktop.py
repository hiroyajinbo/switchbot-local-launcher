from app.desktop import run_desktop
from app.settings import Settings


class FakeEvent:
    def __init__(self) -> None:
        self.callback = None

    def __iadd__(self, callback):
        self.callback = callback
        return self


class FakeWindow:
    def __init__(self) -> None:
        self.events = type("Events", (), {"closed": FakeEvent()})()


class FakeWebview:
    def __init__(self) -> None:
        self.window = FakeWindow()
        self.created = None
        self.started = None

    def create_window(self, title, url, **kwargs):
        self.created = (title, url, kwargs)
        return self.window

    def start(self, **kwargs) -> None:
        self.started = kwargs
        self.window.events.closed.callback()


class FakeServer:
    instances = []

    def __init__(self, application, host, port, **kwargs) -> None:
        self.application = application
        self.host = host
        self.port = port
        self.kwargs = kwargs
        self.start_count = 0
        self.stop_count = 0
        self.instances.append(self)

    def start(self) -> str:
        self.start_count += 1
        return f"http://{self.host}:{self.port}/"

    def stop(self) -> None:
        self.stop_count += 1


class FakeInstance:
    def __init__(self) -> None:
        self.closed = False

    def acquire(self) -> bool:
        return True

    def close(self) -> None:
        self.closed = True


def test_desktop_window_owns_server_lifecycle(tmp_path) -> None:
    FakeServer.instances.clear()
    webview = FakeWebview()
    settings = Settings(
        switchbot_token="token",
        switchbot_secret="secret",
        config_path=str(tmp_path / "config.json"),
        log_path=str(tmp_path / "launcher.log"),
    )

    run_desktop(
        settings=settings,
        webview_module=webview,
        server_factory=FakeServer,
        instance_factory=FakeInstance,
    )

    server = FakeServer.instances[0]
    assert server.application.title == "SwitchBot Local Launcher"
    assert server.start_count == 1
    assert server.stop_count == 2
    assert webview.created[0] == "SwitchBot Local Launcher"
    assert webview.created[1] == "http://127.0.0.1:8765/"
    assert webview.created[2]["min_size"] == (720, 560)
    assert webview.started == {
        "gui": "edgechromium",
        "debug": False,
        "private_mode": False,
        "storage_path": str(tmp_path / "webview"),
    }
    assert (tmp_path / "webview").is_dir()
