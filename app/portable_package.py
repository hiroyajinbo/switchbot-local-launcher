from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from dotenv import dotenv_values

REQUIRED_FILES = {
    ".env.example",
    "README_PORTABLE.md",
    "SwitchBotLocalLauncher.exe",
    "config.example.json",
    "start.cmd",
}
PRIVATE_FILES = {".env", "config.json"}


class PortablePackageError(ValueError):
    pass


def verify_portable_package(
    package_dir: Path,
    zip_path: Path,
    *,
    allow_local_config: bool = False,
    private_values: set[bytes] | None = None,
) -> None:
    package_dir = package_dir.resolve()
    zip_path = zip_path.resolve()
    if not package_dir.is_dir():
        raise PortablePackageError(f"portable folder was not found: {package_dir}")
    if not zip_path.is_file():
        raise PortablePackageError(f"portable ZIP was not found: {zip_path}")

    folder_files = {path.name for path in package_dir.iterdir() if path.is_file()}
    _verify_required_files(folder_files, "portable folder")
    if not allow_local_config:
        _verify_private_files(folder_files, "portable folder")
        _verify_folder_values(package_dir, private_values or set())

    try:
        with ZipFile(zip_path) as archive:
            zip_files = {
                Path(name.replace("\\", "/")).name
                for name in archive.namelist()
                if name and not name.endswith("/") and "/" not in name.rstrip("/")
            }
    except BadZipFile as error:
        raise PortablePackageError(f"portable ZIP is invalid: {zip_path}") from error

    _verify_required_files(zip_files, "portable ZIP")
    if not allow_local_config:
        _verify_private_files(zip_files, "portable ZIP")
        _verify_zip_values(zip_path, private_values or set())


def _verify_required_files(files: set[str], location: str) -> None:
    missing = sorted(REQUIRED_FILES - files)
    if missing:
        raise PortablePackageError(f"{location} is missing required files: {', '.join(missing)}")


def _verify_private_files(files: set[str], location: str) -> None:
    included = sorted(PRIVATE_FILES & files)
    if included:
        raise PortablePackageError(
            f"{location} contains private runtime files: {', '.join(included)}"
        )


def private_values_from_env(env_path: Path | None) -> set[bytes]:
    if env_path is None or not env_path.is_file():
        return set()
    values = dotenv_values(env_path)
    return {
        value.encode("utf-8")
        for key in ("SWITCHBOT_TOKEN", "SWITCHBOT_SECRET")
        if (value := values.get(key)) and len(value) >= 8
    }


def _verify_folder_values(package_dir: Path, private_values: set[bytes]) -> None:
    if not private_values:
        return
    for path in package_dir.rglob("*"):
        if path.is_file() and _contains_private_value(path.read_bytes(), private_values):
            raise PortablePackageError(
                f"portable folder contains a credential value in: {path.relative_to(package_dir)}"
            )


def _verify_zip_values(zip_path: Path, private_values: set[bytes]) -> None:
    if not private_values:
        return
    with ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if not info.is_dir() and _contains_private_value(archive.read(info), private_values):
                raise PortablePackageError(
                    f"portable ZIP contains a credential value in: {info.filename}"
                )


def _contains_private_value(content: bytes, private_values: set[bytes]) -> bool:
    return any(value in content for value in private_values)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a portable launcher package.")
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--zip-path", type=Path, required=True)
    parser.add_argument("--allow-local-config", action="store_true")
    parser.add_argument("--source-env", type=Path)
    args = parser.parse_args()
    try:
        verify_portable_package(
            args.package_dir,
            args.zip_path,
            allow_local_config=args.allow_local_config,
            private_values=private_values_from_env(args.source_env),
        )
    except PortablePackageError as error:
        print(f"ERROR: {error}")
        return 1
    print("Portable package verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
