from __future__ import annotations

import ctypes
from types import TracebackType
from typing import Any, Protocol

from app.errors import LauncherError

ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "Local\\SwitchBotLocalLauncher"


class Kernel32Protocol(Protocol):
    def CreateMutexW(self, attributes: Any, initial_owner: bool, name: str) -> int: ...

    def CloseHandle(self, handle: int) -> bool: ...


class SingleInstance:
    """Keep a named Windows mutex alive for the desktop process lifetime."""

    def __init__(
        self,
        name: str = MUTEX_NAME,
        *,
        kernel32: Kernel32Protocol | None = None,
        get_last_error=ctypes.get_last_error,
    ) -> None:
        self.name = name
        self._kernel32 = kernel32
        self._get_last_error = get_last_error
        self._handle: int | None = None
        self.acquired = False

    def acquire(self) -> bool:
        if self._handle is not None:
            return self.acquired
        kernel32 = self._kernel32 or _load_kernel32()
        handle = kernel32.CreateMutexW(None, False, self.name)
        if not handle:
            raise LauncherError("PCアプリの単一起動制御を初期化できませんでした。")
        self._kernel32 = kernel32
        self._handle = handle
        self.acquired = self._get_last_error() != ERROR_ALREADY_EXISTS
        if not self.acquired:
            self.close()
        return self.acquired

    def close(self) -> None:
        if self._handle is not None and self._kernel32 is not None:
            self._kernel32.CloseHandle(self._handle)
        self._handle = None

    def __enter__(self) -> SingleInstance:
        self.acquire()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self.close()


def _load_kernel32() -> Kernel32Protocol:
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except (AttributeError, OSError) as exc:
        raise LauncherError("PCアプリの単一起動制御はWindowsでのみ利用できます。") from exc
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_bool
    return kernel32
