# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

PROJECT_DIR = Path(SPEC).resolve().parent

a = Analysis(
    [str(PROJECT_DIR / "desktop_entry.py")],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=[(str(PROJECT_DIR / "app" / "web"), "app/web")],
    hiddenimports=["app.main"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "cefpython3",
        "tkinter",
        "pywinauto",
        "comtypes",
        "win32com",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SwitchBotLocalLauncher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="SwitchBotLocalLauncher",
)
