from __future__ import annotations

import socket
import threading
import time
from collections.abc import Callable
from logging.config import dictConfig
from pathlib import Path
from typing import Any, Protocol

import uvicorn

from app.errors import LauncherError


class ServerProtocol(Protocol):
    started: bool
    should_exit: bool
    force_exit: bool

    def run(self) -> None: ...


ServerFactory = Callable[[uvicorn.Config], ServerProtocol]


class ManagedServer:
    """Run Uvicorn in a thread that can be owned by a desktop window."""

    def __init__(
        self,
        application: Any,
        host: str,
        port: int,
        *,
        startup_timeout: float = 10.0,
        shutdown_timeout: float = 10.0,
        server_factory: ServerFactory = uvicorn.Server,
        log_config: dict[str, Any] | None = None,
    ) -> None:
        self._application = application
        self.host = host
        self.port = port
        self.startup_timeout = startup_timeout
        self.shutdown_timeout = shutdown_timeout
        self._server_factory = server_factory
        self._log_config = log_config
        self._server: ServerProtocol | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(
            self._server is not None
            and self._server.started
            and self._thread is not None
            and self._thread.is_alive()
        )

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def start(self) -> str:
        if self.running:
            return self.url
        if self._thread is not None and self._thread.is_alive():
            raise LauncherError("サーバーは起動処理中です。")

        ensure_port_available(self.host, self.port)
        config = uvicorn.Config(
            self._application,
            host=self.host,
            port=self.port,
            reload=False,
            log_config=self._log_config,
        )
        self._server = self._server_factory(config)
        self._thread = threading.Thread(
            target=self._server.run,
            name="switchbot-local-server",
        )
        self._thread.start()

        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self._server.started:
                return self.url
            if not self._thread.is_alive():
                self._clear_stopped_server()
                raise LauncherError(
                    "ローカルサーバーを起動できませんでした。ログを確認してください。"
                )
            time.sleep(0.01)

        self.stop()
        raise LauncherError(
            f"ローカルサーバーの起動が{self.startup_timeout:g}秒以内に完了しませんでした。"
        )

    def stop(self) -> None:
        server = self._server
        thread = self._thread
        if server is None or thread is None:
            return

        server.should_exit = True
        thread.join(self.shutdown_timeout)
        if thread.is_alive():
            server.force_exit = True
            thread.join(1.0)
        if thread.is_alive():
            raise LauncherError("ローカルサーバーを正常に終了できませんでした。")
        self._clear_stopped_server()

    def wait(self) -> None:
        if self._thread is not None:
            self._thread.join()

    def _clear_stopped_server(self) -> None:
        self._server = None
        self._thread = None

    def __enter__(self) -> ManagedServer:
        self.start()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.stop()


def ensure_port_available(host: str, port: int) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((host, port))
    except OSError as exc:
        raise LauncherError(
            f"{host}:{port} は既に使用されています。起動済みのアプリを確認してください。"
        ) from exc


def configure_rotating_logging(log_path: str | Path) -> dict[str, Any]:
    path = Path(log_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
            },
            "access": {
                "format": (
                    '%(asctime)s %(levelname)s %(client_addr)s "%(request_line)s" '
                    "%(status_code)s"
                ),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": str(path),
                "maxBytes": 1_048_576,
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "access_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "access",
                "filename": str(path),
                "maxBytes": 1_048_576,
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {
                "handlers": ["console", "access_file"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    dictConfig(config)
    return config
