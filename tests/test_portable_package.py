from pathlib import Path
from zipfile import ZipFile

import pytest

from app.portable_package import (
    PRIVATE_FILES,
    REQUIRED_FILES,
    PortablePackageError,
    verify_portable_package,
)


def create_package(tmp_path: Path, extra_files: set[str] | None = None) -> tuple[Path, Path]:
    package_dir = tmp_path / "SwitchBotLocalLauncher-portable"
    package_dir.mkdir()
    files = REQUIRED_FILES | (extra_files or set())
    for name in files:
        (package_dir / name).write_bytes(b"test")
    zip_path = tmp_path / "SwitchBotLocalLauncher-portable.zip"
    with ZipFile(zip_path, "w") as archive:
        for name in files:
            archive.writestr(name, b"test")
    return package_dir, zip_path


def test_accepts_clean_portable_package(tmp_path: Path) -> None:
    package_dir, zip_path = create_package(tmp_path)

    verify_portable_package(package_dir, zip_path)


@pytest.mark.parametrize("private_file", sorted(PRIVATE_FILES))
def test_rejects_private_runtime_file_in_folder(tmp_path: Path, private_file: str) -> None:
    package_dir, zip_path = create_package(tmp_path)
    (package_dir / private_file).write_text("private", encoding="utf-8")

    with pytest.raises(PortablePackageError, match="private runtime files"):
        verify_portable_package(package_dir, zip_path)


@pytest.mark.parametrize("private_file", sorted(PRIVATE_FILES))
def test_rejects_private_runtime_file_in_zip(tmp_path: Path, private_file: str) -> None:
    package_dir, zip_path = create_package(tmp_path)
    with ZipFile(zip_path, "a") as archive:
        archive.writestr(private_file, "private")

    with pytest.raises(PortablePackageError, match="private runtime files"):
        verify_portable_package(package_dir, zip_path)


def test_allows_explicit_personal_package(tmp_path: Path) -> None:
    package_dir, zip_path = create_package(tmp_path, PRIVATE_FILES)

    verify_portable_package(package_dir, zip_path, allow_local_config=True)


def test_rejects_credential_value_in_folder(tmp_path: Path) -> None:
    package_dir, zip_path = create_package(tmp_path)
    secret = b"credential-value-123"
    (package_dir / "unexpected.txt").write_bytes(b"prefix-" + secret)

    with pytest.raises(PortablePackageError, match="credential value"):
        verify_portable_package(package_dir, zip_path, private_values={secret})


def test_rejects_credential_value_in_zip(tmp_path: Path) -> None:
    package_dir, zip_path = create_package(tmp_path)
    secret = b"credential-value-123"
    with ZipFile(zip_path, "a") as archive:
        archive.writestr("unexpected.txt", b"prefix-" + secret)

    with pytest.raises(PortablePackageError, match="credential value"):
        verify_portable_package(package_dir, zip_path, private_values={secret})


def test_rejects_missing_required_file(tmp_path: Path) -> None:
    package_dir, zip_path = create_package(tmp_path)
    (package_dir / "start.cmd").unlink()

    with pytest.raises(PortablePackageError, match="missing required files"):
        verify_portable_package(package_dir, zip_path)
