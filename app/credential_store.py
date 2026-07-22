from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes
from dataclasses import dataclass
from typing import Protocol

from app.errors import CredentialStoreError

CREDENTIAL_TARGET = "SwitchBotLocalLauncher/SwitchBotAPI"
_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2
_ERROR_NOT_FOUND = 1168


@dataclass(frozen=True)
class StoredCredentials:
    token: str
    secret: str


class CredentialStore(Protocol):
    @property
    def available(self) -> bool: ...

    def load(self) -> StoredCredentials | None: ...

    def save(self, credentials: StoredCredentials) -> None: ...

    def delete(self) -> None: ...


class _CredentialW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.c_void_p),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class WindowsCredentialStore:
    """Store SwitchBot API secrets in the current user's Windows Credential Manager."""

    def __init__(self, target: str = CREDENTIAL_TARGET) -> None:
        self.target = target

    @property
    def available(self) -> bool:
        return os.name == "nt"

    def load(self) -> StoredCredentials | None:
        if not self.available:
            return None

        api = self._api()
        credential_pointer = ctypes.POINTER(_CredentialW)()
        if not api.CredReadW(
            self.target,
            _CRED_TYPE_GENERIC,
            0,
            ctypes.byref(credential_pointer),
        ):
            error_code = ctypes.get_last_error()
            if error_code == _ERROR_NOT_FOUND:
                return None
            raise CredentialStoreError(
                f"Windows資格情報を読み込めませんでした。エラーコード: {error_code}"
            )

        try:
            credential = credential_pointer.contents
            raw = ctypes.string_at(
                credential.CredentialBlob,
                credential.CredentialBlobSize,
            )
            payload = json.loads(raw.decode("utf-8"))
            token = str(payload.get("token", "")).strip()
            secret = str(payload.get("secret", "")).strip()
            if not token or not secret:
                raise CredentialStoreError("保存済みのSwitchBot認証情報が不完全です。")
            return StoredCredentials(token=token, secret=secret)
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as exc:
            raise CredentialStoreError("保存済みのSwitchBot認証情報を読み取れません。") from exc
        finally:
            api.CredFree(credential_pointer)

    def save(self, credentials: StoredCredentials) -> None:
        if not self.available:
            raise CredentialStoreError("この環境ではWindows資格情報を利用できません。")

        token = credentials.token.strip()
        secret = credentials.secret.strip()
        if not token or not secret:
            raise CredentialStoreError("Open TokenとSecret Keyを両方入力してください。")

        raw = json.dumps(
            {"token": token, "secret": secret},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        blob = ctypes.create_string_buffer(raw)
        credential = _CredentialW()
        credential.Type = _CRED_TYPE_GENERIC
        credential.TargetName = self.target
        credential.Comment = "SwitchBot Local Launcher API credentials"
        credential.CredentialBlobSize = len(raw)
        credential.CredentialBlob = ctypes.cast(blob, ctypes.c_void_p).value
        credential.Persist = _CRED_PERSIST_LOCAL_MACHINE
        credential.UserName = "SwitchBot API"

        api = self._api()
        if not api.CredWriteW(ctypes.byref(credential), 0):
            error_code = ctypes.get_last_error()
            raise CredentialStoreError(
                f"Windows資格情報へ保存できませんでした。エラーコード: {error_code}"
            )

    def delete(self) -> None:
        if not self.available:
            return

        api = self._api()
        if api.CredDeleteW(self.target, _CRED_TYPE_GENERIC, 0):
            return
        error_code = ctypes.get_last_error()
        if error_code != _ERROR_NOT_FOUND:
            raise CredentialStoreError(
                f"Windows資格情報を削除できませんでした。エラーコード: {error_code}"
            )

    @staticmethod
    def _api():
        api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        credential_pointer = ctypes.POINTER(_CredentialW)
        api.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(credential_pointer),
        ]
        api.CredReadW.restype = wintypes.BOOL
        api.CredWriteW.argtypes = [ctypes.POINTER(_CredentialW), wintypes.DWORD]
        api.CredWriteW.restype = wintypes.BOOL
        api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        api.CredDeleteW.restype = wintypes.BOOL
        api.CredFree.argtypes = [ctypes.c_void_p]
        api.CredFree.restype = None
        return api
