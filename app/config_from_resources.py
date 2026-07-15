import argparse
import json
import re
from pathlib import Path
from typing import Any

from app.config import LauncherConfig

DEFAULT_INPUT_PATH = Path("switchbot.resources.json")
DEFAULT_OUTPUT_PATH = Path("config.generated.json")


def build_config_from_resources(resources: dict[str, Any]) -> dict[str, Any]:
    scenes = resources.get("scenes", [])
    if not isinstance(scenes, list):
        scenes = []

    buttons = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            continue
        scene_id = scene.get("sceneId")
        scene_name = scene.get("sceneName") or f"Scene {index}"
        if not scene_id:
            continue
        buttons.append(
            {
                "id": _button_id("scene", scene_name, index),
                "label": scene_name,
                "group": "シーン",
                "type": "scene",
                "scene_id": scene_id,
            }
        )

    return {"buttons": buttons}


def write_config_template(input_path: Path, output_path: Path) -> int:
    resources = json.loads(input_path.read_text(encoding="utf-8"))
    config = build_config_from_resources(resources)
    LauncherConfig.model_validate(config)
    output_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(config["buttons"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()

    count = write_config_template(Path(args.input), Path(args.output))
    print(f"Generated {args.output} with {count} scene button(s).")
    print("Review it, then copy the buttons you want into config.json.")


def _button_id(prefix: str, label: str, index: int) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_").lower()
    if not normalized:
        normalized = f"{index:03d}"
    return f"{prefix}_{normalized}"


if __name__ == "__main__":
    main()
