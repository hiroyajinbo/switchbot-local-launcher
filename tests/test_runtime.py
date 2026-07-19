import logging
import socket
import threading

import pytest

from app.errors import LauncherError
from app.runtime import (
    ManagedServer,
    configure_rotating_logging,
    ensure_port_available,
)


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


def test_rotating_log_is_created_and_writable(tmp_path) -> None:
    log_path = tmp_path / "logs" / "launcher.log"

    config = configure_rotating_logging(log_path)
    logging.getLogger("uvicorn.error").info("runtime test")
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d',
        "127.0.0.1:12345",
        "GET",
        "/api/health",
        "1.1",
        200,
    )
    for logger_name in ("uvicorn", "uvicorn.access"):
        for handler in logging.getLogger(logger_name).handlers:
            handler.flush()

    assert config["handlers"]["file"]["maxBytes"] == 1_048_576
    assert config["handlers"]["file"]["backupCount"] == 5
    contents = log_path.read_text(encoding="utf-8")
    assert "runtime test" in contents
    assert 'GET /api/health HTTP/1.1" 200' in contents
