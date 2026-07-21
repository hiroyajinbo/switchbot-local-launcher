from pathlib import Path

import pytest

from app.data_paths import (
    PORTABLE_DATA_ROOT_ENV,
    AppDataPaths,
    desktop_data_paths,
    load_desktop_settings,
    prepare_desktop_data,
)
from app.errors import LauncherError


def test_desktop_data_paths_use_local_app_data(tmp_path) -> None:
    paths = desktop_data_paths({"LOCALAPPDATA": str(tmp_path)})

    assert paths.root == tmp_path / "SwitchBotLocalLauncher"


def test_desktop_data_paths_can_use_portable_root(tmp_path) -> None:
    paths = desktop_data_paths(
        {
            PORTABLE_DATA_ROOT_ENV: str(tmp_path / "portable"),
            "LOCALAPPDATA": str(tmp_path / "local"),
        }
    )

    assert paths.root == tmp_path / "portable"


def test_prepare_desktop_data_copies_once_without_overwrite(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / ".env").write_text("SWITCHBOT_TOKEN=one", encoding="utf-8")
    (source / "config.json").write_text('{"buttons": []}', encoding="utf-8")
    paths = AppDataPaths(tmp_path / "local")

    prepare_desktop_data(source, paths=paths)
    (source / ".env").write_text("SWITCHBOT_TOKEN=two", encoding="utf-8")
    prepare_desktop_data(source, paths=paths)

    assert paths.env.read_text(encoding="utf-8") == "SWITCHBOT_TOKEN=one"
    assert paths.config.read_text(encoding="utf-8") == '{"buttons": []}'


def test_prepare_desktop_data_reports_missing_files(tmp_path) -> None:
    with pytest.raises(LauncherError, match="設定ファイルがありません"):
        prepare_desktop_data(tmp_path / "empty", paths=AppDataPaths(tmp_path / "local"))


def test_desktop_settings_resolve_relative_paths_inside_data_root(tmp_path, monkeypatch) -> None:
    paths = AppDataPaths(tmp_path / "local")
    paths.root.mkdir()
    paths.env.write_text(
        "\n".join(
            [
                "SWITCHBOT_TOKEN=token",
                "SWITCHBOT_SECRET=secret",
                "SWITCHBOT_CONFIG_PATH=settings/config.json",
                "SWITCHBOT_LOG_PATH=diagnostics/launcher.log",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("SWITCHBOT_TOKEN", raising=False)
    monkeypatch.delenv("SWITCHBOT_SECRET", raising=False)
    monkeypatch.delenv("SWITCHBOT_CONFIG_PATH", raising=False)
    monkeypatch.delenv("SWITCHBOT_LOG_PATH", raising=False)

    settings = load_desktop_settings(paths)

    assert Path(settings.config_path) == paths.root / "settings" / "config.json"
    assert Path(settings.log_path) == paths.root / "diagnostics" / "launcher.log"
