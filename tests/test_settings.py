import pytest

from app.credential_store import StoredCredentials
from app.errors import SecretConfigError
from app.settings import load_settings


class FakeCredentialStore:
    def __init__(self, credentials: StoredCredentials | None = None) -> None:
        self.available = True
        self.credentials = credentials

    def load(self) -> StoredCredentials | None:
        return self.credentials

    def save(self, credentials: StoredCredentials) -> None:
        self.credentials = credentials


def clear_credentials(monkeypatch) -> None:
    monkeypatch.delenv("SWITCHBOT_TOKEN", raising=False)
    monkeypatch.delenv("SWITCHBOT_SECRET", raising=False)


def test_load_settings_uses_windows_credentials_when_env_is_missing(tmp_path, monkeypatch) -> None:
    clear_credentials(monkeypatch)
    store = FakeCredentialStore(StoredCredentials(token="stored-token", secret="stored-secret"))

    settings = load_settings(tmp_path / "missing.env", credential_store=store)

    assert settings.switchbot_token == "stored-token"
    assert settings.switchbot_secret == "stored-secret"
    assert settings.credentials_source == "windows"


def test_load_settings_prefers_complete_env_credentials(tmp_path, monkeypatch) -> None:
    clear_credentials(monkeypatch)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SWITCHBOT_TOKEN=env-token\nSWITCHBOT_SECRET=env-secret\n",
        encoding="utf-8",
    )
    store = FakeCredentialStore(StoredCredentials(token="stored-token", secret="stored-secret"))

    settings = load_settings(env_path, credential_store=store)

    assert settings.switchbot_token == "env-token"
    assert settings.switchbot_secret == "env-secret"
    assert settings.credentials_source == "env"


def test_load_settings_can_boot_without_credentials_for_setup(tmp_path, monkeypatch) -> None:
    clear_credentials(monkeypatch)

    settings = load_settings(
        tmp_path / "missing.env",
        credential_store=FakeCredentialStore(),
        allow_missing_credentials=True,
    )

    assert settings.switchbot_token == ""
    assert settings.switchbot_secret == ""
    assert settings.credentials_source == "missing"


def test_load_settings_reports_missing_credentials(tmp_path, monkeypatch) -> None:
    clear_credentials(monkeypatch)

    with pytest.raises(SecretConfigError, match="初回設定"):
        load_settings(tmp_path / "missing.env", credential_store=FakeCredentialStore())
