import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import DeviceCommandButton, LauncherConfig, SceneButton, load_config
from app.config_device_commands import build_device_command_config
from app.config_from_resources import build_config_from_resources
from app.errors import ConfigError
from app.switchbot_client import SwitchBotClient


class ConfigCandidate(BaseModel):
    id: str
    label: str
    group: str
    type: str


class ConfigCandidateList(BaseModel):
    candidates: list[ConfigCandidate]
    stale: list[ConfigCandidate]


class ApplyCandidatesRequest(BaseModel):
    ids: list[str]


class ApplyCandidatesResult(BaseModel):
    added: int
    skipped: int
    restart_required: bool = True


class ButtonAppearanceUpdate(BaseModel):
    icon: str
    icon_badge: str


class ConfigSyncService:
    def __init__(self, config_path: Path, client: SwitchBotClient) -> None:
        self._config_path = config_path
        self._client = client
        self._candidates: dict[str, dict[str, Any]] = {}

    def current_config(self) -> LauncherConfig:
        return load_config(self._config_path)

    async def refresh(self) -> ConfigCandidateList:
        devices_body = (await self._client.get_devices()).get("body", {})
        scenes = (await self._client.get_scenes()).get("body", [])
        resources = {"devices": devices_body, "scenes": scenes}
        generated = [
            *build_config_from_resources(resources)["buttons"],
            *build_device_command_config(resources)["buttons"],
        ]
        existing_ids = {button.id for button in load_config(self._config_path).buttons}
        self._candidates = {
            item["id"]: item for item in generated if item["id"] not in existing_ids
        }
        config = load_config(self._config_path)
        scene_ids = {item.get("sceneId") for item in scenes if isinstance(item, dict)}
        device_ids = {
            item.get("deviceId")
            for item in devices_body.get("deviceList", [])
            if isinstance(item, dict)
        }
        stale = []
        for button in config.buttons:
            missing = (
                isinstance(button, SceneButton) and button.scene_id not in scene_ids
            ) or (
                isinstance(button, DeviceCommandButton) and button.device_id not in device_ids
            )
            if missing:
                stale.append(ConfigCandidate.model_validate(button.model_dump()))
        return ConfigCandidateList(
            candidates=[ConfigCandidate.model_validate(item) for item in self._candidates.values()],
            stale=stale,
        )

    def apply(self, ids: list[str]) -> ApplyCandidatesResult:
        unique_ids = list(dict.fromkeys(ids))
        unknown = [
            candidate_id for candidate_id in unique_ids if candidate_id not in self._candidates
        ]
        if unknown:
            raise ConfigError(f"取得候補にないボタンIDです: {', '.join(unknown)}")

        config = load_config(self._config_path)
        existing_ids = {button.id for button in config.buttons}
        additions = [
            self._candidates[candidate_id]
            for candidate_id in unique_ids
            if candidate_id not in existing_ids
        ]
        merged = config.model_dump()
        merged["buttons"] = [button.model_dump() for button in config.buttons] + additions
        validated = LauncherConfig.model_validate(merged)
        temporary_path = self._config_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(validated.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_path.replace(self._config_path)
        return ApplyCandidatesResult(added=len(additions), skipped=len(unique_ids) - len(additions))

    def set_button_lock(self, button_id: str, locked: bool) -> dict[str, Any]:
        config = load_config(self._config_path)
        button = config.get_button(button_id)
        if button is None:
            raise ConfigError(f"未定義のボタンIDです: {button_id}")
        raw = config.model_dump()
        for item in raw["buttons"]:
            if item["id"] == button_id:
                item["locked"] = locked
        self._write(raw)
        return {"id": button_id, "locked": locked}

    def set_button_appearance(
        self, button_id: str, update: ButtonAppearanceUpdate
    ) -> dict[str, Any]:
        config = load_config(self._config_path)
        if config.get_button(button_id) is None:
            raise ConfigError(f"未定義のボタンIDです: {button_id}")
        raw = config.model_dump()
        for item in raw["buttons"]:
            if item["id"] == button_id:
                item["icon"] = update.icon
                item["icon_badge"] = update.icon_badge
        self._write(raw)
        saved = load_config(self._config_path).get_button(button_id)
        return {
            "id": button_id,
            "icon": saved.icon,
            "icon_badge": saved.icon_badge,
        }

    def remove_buttons(self, ids: list[str]) -> dict[str, int]:
        config = load_config(self._config_path)
        unique_ids = set(ids)
        raw = config.model_dump()
        raw["buttons"] = [item for item in raw["buttons"] if item["id"] not in unique_ids]
        if not raw["buttons"]:
            raise ConfigError("すべてのボタンは削除できません。")
        removed = len(config.buttons) - len(raw["buttons"])
        self._write(raw)
        return {"removed": removed}

    def _write(self, raw: dict[str, Any]) -> None:
        validated = LauncherConfig.model_validate(raw)
        temporary_path = self._config_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(validated.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_path.replace(self._config_path)
