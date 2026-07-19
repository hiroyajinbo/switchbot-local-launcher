import socket
import threading

import pytest

from app.errors import LauncherError
from app.runtime import ManagedServer, ensure_port_available


class FakeServer:
    def __init__(self, _config) -> None:
        self.started = False
        self.should_exit = False
        self.force_exit = False

    def run(self) -> None:
        self.started = True
        while not self.should_exit and not self.force_exit:
            threading.Event().wait(0.01)


class FailedServer(FakeServer):
    def run(self) -> None:
        return


def unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_managed_server_starts_and_stops() -> None:
    server = ManagedServer(object(), "127.0.0.1", unused_port(), server_factory=FakeServer)

    assert server.start() == server.url
    assert server.running is True

    server.stop()

    assert server.running is False


def test_managed_server_reports_startup_failure() -> None:
    server = ManagedServer(object(), "127.0.0.1", unused_port(), server_factory=FailedServer)

    with pytest.raises(LauncherError, match="起動できませんでした"):
        server.start()


def test_port_conflict_has_user_friendly_message() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

        with pytest.raises(LauncherError, match="既に使用されています"):
            ensure_port_available("127.0.0.1", port)
