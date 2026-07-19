from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from pywinauto import Desktop

HOST = "127.0.0.1"
PORT = 8765
WINDOW_TITLE = "SwitchBot Local Launcher"
PROJECT_DIR = Path(__file__).resolve().parents[1]


def wait_for_health(timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://{HOST}:{PORT}/api/health", timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, URLError) as exc:
            last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"ヘルスAPIが{timeout:g}秒以内に応答しませんでした: {last_error}")


def ensure_port_released(timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=0.2):
                pass
        except OSError:
            return
        time.sleep(0.2)
    raise RuntimeError(f"終了後も{HOST}:{PORT}が使用されています。")


def run_smoke_test(hold_seconds: float) -> None:
    ensure_port_released(1)
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output:
        process = subprocess.Popen(
            [sys.executable, "-m", "app.desktop"],
            cwd=PROJECT_DIR,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            wait_for_health(30)
            window = Desktop(backend="uia").window(title=WINDOW_TITLE)
            window.wait("visible enabled ready", timeout=30)
            rectangle = window.rectangle()
            print(
                f"OK: ウィンドウを検出しました "
                f"({rectangle.width()}x{rectangle.height()}, PID={process.pid})"
            )
            duplicate = subprocess.run(
                [sys.executable, "-m", "app.desktop"],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if duplicate.returncode != 0:
                raise RuntimeError(
                    f"二重起動プロセスが終了コード{duplicate.returncode}で終了しました。\n"
                    f"{duplicate.stdout}{duplicate.stderr}"
                )
            if process.poll() is not None:
                raise RuntimeError("二重起動の確認中に既存アプリが終了しました。")
            print("OK: 二重起動を防止し、既存アプリだけが動作しています。")
            time.sleep(hold_seconds)
            window.close()
            process.wait(timeout=20)
            if process.returncode != 0:
                raise RuntimeError(f"PCアプリが終了コード{process.returncode}で終了しました。")
            ensure_port_released(10)
            output.seek(0)
            logs = output.read()
            if "--- Logging error ---" in logs or "Traceback (most recent call last)" in logs:
                raise RuntimeError(f"PCアプリのログに例外が記録されました。\n{logs}")
            print("OK: ウィンドウ終了後にプロセスとポートが解放されました。")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(description="PCアプリのWindows GUIスモークテスト")
    parser.add_argument(
        "--hold-seconds",
        type=float,
        default=15.0,
        help="検出したウィンドウを表示しておく秒数（既定: 15秒）",
    )
    args = parser.parse_args()
    run_smoke_test(args.hold_seconds)


if __name__ == "__main__":
    main()
