import json
from pathlib import Path

EXTENSION_DIR = Path(__file__).parents[1] / "browser_extension"


def test_browser_extension_manifest_has_only_local_api_permission():
    manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == 3
    assert manifest["action"]["default_popup"] == "popup.html"
    assert manifest["host_permissions"] == ["http://127.0.0.1:8765/*"]
    assert "permissions" not in manifest


def test_browser_extension_assets_exist_and_do_not_contain_credentials():
    for name in ("popup.html", "popup.css", "popup.js"):
        assert (EXTENSION_DIR / name).is_file()
    script = (EXTENSION_DIR / "popup.js").read_text(encoding="utf-8")

    assert '"scene", "remote_command"' in script
    assert "/api/actions/" in script
    assert "SWITCHBOT_TOKEN" not in script
    assert "SWITCHBOT_SECRET" not in script
