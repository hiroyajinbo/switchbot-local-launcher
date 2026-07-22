import hashlib
import json
import re
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator

from app.config import (
    DeviceCommandButton,
    LauncherConfig,
    QuickIcon,
    QuickIconBadge,
    RemoteCommandButton,
    SceneButton,
    load_config,
)
from app.config_device_commands import build_device_command_config
from app.config_from_resources import build_config_from_resources
from app.errors import ConfigError
from app.switchbot_client import SwitchBotClient


class ConfigCandidate(BaseModel):
    id: str
    label: str
    group: str
    type: str
    source_id: str | None = None


class ConfigCandidateList(BaseModel):
    candidates: list[ConfigCandidate]
    stale: list[ConfigCandidate]
    excluded_scenes: list[ConfigCandidate] = Field(default_factory=list)
    scene_auto_add: bool = False
    auto_added: int = 0


class ApplyCandidatesRequest(BaseModel):
    ids: list[str]


class ApplyCandidatesResult(BaseModel):
    added: int
    skipped: int
    restart_required: bool = True


class ButtonAppearanceUpdate(BaseModel):
    icon: str
    icon_badge: str
    group: str | None = Field(default=None, min_length=1, max_length=40)


class SceneSyncUpdate(BaseModel):
    auto_add: bool


class QuickActionGroupOrderUpdate(BaseModel):
    groups: list[str]


class RemoteQuickActionUpdate(BaseModel):
    label: Annotated[str, Field(min_length=1)]
    group: Annotated[str, Field(min_length=1)] = "リモコン"
    device_id: Annotated[str, Field(min_length=1)]
    command: str = "setAll"
    parameter: str
    icon: QuickIcon = "climate"
    icon_badge: QuickIconBadge = "none"
    overwrite: bool = False

    @model_validator(mode="after")
    def validate_command(self) -> "RemoteQuickActionUpdate":
        valid_set_all = self.command == "setAll" and re.fullmatch(
            r"\d+,[1-5],[1-4],on", self.parameter
        )
        valid_turn_off = self.command == "turnOff" and self.parameter == "default"
        if not valid_set_all and not valid_turn_off:
            raise ValueError("リモコン操作の形式が不正です。")
        return self


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
        config = load_config(self._config_path)
        existing_ids = {button.id for button in config.buttons}
        existing_scene_ids = {
            button.scene_id for button in config.buttons if isinstance(button, SceneButton)
        }
        excluded_scene_ids = set(config.scene_sync.excluded_scene_ids)
        candidate_items: list[dict[str, Any]] = []
        excluded_items: list[dict[str, Any]] = []
        for item in generated:
            if item["type"] == "scene":
                if item["scene_id"] in existing_scene_ids:
                    continue
                if item["scene_id"] in excluded_scene_ids:
                    excluded_items.append(item)
                    continue
            elif item["id"] in existing_ids:
                continue
            candidate_items.append(item)

        self._candidates = {item["id"]: item for item in candidate_items}
        auto_added = 0
        if config.scene_sync.auto_add:
            scene_candidate_ids = [
                candidate_id
                for candidate_id, item in self._candidates.items()
                if item["type"] == "scene"
            ]
            if scene_candidate_ids:
                auto_added = self.apply(scene_candidate_ids).added
                self._candidates = {
                    candidate_id: item
                    for candidate_id, item in self._candidates.items()
                    if candidate_id not in scene_candidate_ids
                }
                config = load_config(self._config_path)

        scene_ids = {item.get("sceneId") for item in scenes if isinstance(item, dict)}
        device_ids = {
            item.get("deviceId")
            for item in devices_body.get("deviceList", [])
            if isinstance(item, dict)
        }
        remote_ids = {
            item.get("deviceId")
            for item in devices_body.get("infraredRemoteList", [])
            if isinstance(item, dict)
        }
        stale = []
        for button in config.buttons:
            missing = (
                isinstance(button, SceneButton) and button.scene_id not in scene_ids
            ) or (
                isinstance(button, DeviceCommandButton) and button.device_id not in device_ids
            ) or (
                isinstance(button, RemoteCommandButton) and button.device_id not in remote_ids
            )
            if missing:
                stale.append(self._to_candidate(button.model_dump()))

        excluded_by_id = {item["scene_id"]: item for item in excluded_items}
        excluded_labels = config.scene_sync.excluded_scene_labels
        excluded_scenes = [
            self._to_candidate(
                excluded_by_id.get(
                    scene_id,
                    {
                        "id": f"excluded_scene_{scene_id}",
                        "label": excluded_labels.get(scene_id, scene_id),
                        "group": "シーン",
                        "type": "scene",
                        "scene_id": scene_id,
                    },
                )
            )
            for scene_id in config.scene_sync.excluded_scene_ids
        ]
        return ConfigCandidateList(
            candidates=[self._to_candidate(item) for item in self._candidates.values()],
            stale=stale,
            excluded_scenes=excluded_scenes,
            scene_auto_add=config.scene_sync.auto_add,
            auto_added=auto_added,
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
        group = update.group.strip() if update.group is not None else None
        if update.group is not None and not group:
            raise ConfigError("グループ名を入力してください。")
        if group is not None and group not in self._effective_quick_action_groups(config):
            raise ConfigError("先にクイック操作グループを追加してください。")
        raw = config.model_dump()
        for item in raw["buttons"]:
            if item["id"] == button_id:
                item["icon"] = update.icon
                item["icon_badge"] = update.icon_badge
                if group is not None:
                    item["group"] = group
        self._write(raw)
        saved = load_config(self._config_path).get_button(button_id)
        return {
            "id": button_id,
            "icon": saved.icon,
            "icon_badge": saved.icon_badge,
            "group": saved.group,
        }

    def quick_action_groups(self) -> list[str]:
        return self._effective_quick_action_groups(load_config(self._config_path))

    def add_quick_action_group(self, group: str) -> list[str]:
        group = group.strip()
        if not group:
            return self.quick_action_groups()
        if len(group) > 40:
            raise ConfigError("グループ名は40文字以内で入力してください。")
        config = load_config(self._config_path)
        groups = self._effective_quick_action_groups(config)
        if group not in groups:
            groups.append(group)
            raw = config.model_dump()
            raw["quick_action_groups"] = groups
            self._write(raw)
        return groups

    def reorder_quick_action_groups(self, groups: list[str]) -> list[str]:
        config = load_config(self._config_path)
        current = self._effective_quick_action_groups(config)
        if len(groups) != len(set(groups)) or set(groups) != set(current):
            raise ConfigError("グループの並び順が現在の一覧と一致しません。")
        raw = config.model_dump()
        raw["quick_action_groups"] = groups
        self._write(raw)
        return groups

    def remove_quick_action_group(self, group: str) -> dict[str, Any]:
        group = group.strip()
        if group == "シーン":
            raise ConfigError("既定グループ「シーン」は削除できません。")
        config = load_config(self._config_path)
        groups = self._effective_quick_action_groups(config)
        if group not in groups:
            raise ConfigError("削除するグループが見つかりません。")

        raw = config.model_dump()
        moved = 0
        for button in raw["buttons"]:
            if button["type"] in {"scene", "remote_command"} and button["group"] == group:
                button["group"] = "シーン"
                moved += 1
        raw["quick_action_groups"] = [item for item in groups if item != group]
        if "シーン" not in raw["quick_action_groups"]:
            raw["quick_action_groups"].append("シーン")
        self._write(raw)
        return {
            "removed": group,
            "moved_buttons": moved,
            "groups": raw["quick_action_groups"],
        }

    def remove_buttons(self, ids: list[str]) -> dict[str, int]:
        config = load_config(self._config_path)
        unique_ids = set(ids)
        raw = config.model_dump()
        excluded_scene_ids = list(config.scene_sync.excluded_scene_ids)
        excluded_scene_labels = dict(config.scene_sync.excluded_scene_labels)
        for button in config.buttons:
            if button.id in unique_ids and isinstance(button, SceneButton):
                if button.scene_id not in excluded_scene_ids:
                    excluded_scene_ids.append(button.scene_id)
                excluded_scene_labels[button.scene_id] = button.label
        raw["buttons"] = [item for item in raw["buttons"] if item["id"] not in unique_ids]
        raw["scene_sync"]["excluded_scene_ids"] = excluded_scene_ids
        raw["scene_sync"]["excluded_scene_labels"] = excluded_scene_labels
        removed = len(config.buttons) - len(raw["buttons"])
        self._write(raw)
        return {"removed": removed}

    def remove_scene(self, button_id: str) -> dict[str, Any]:
        config = load_config(self._config_path)
        button = config.get_button(button_id)
        if button is None:
            raise ConfigError(f"未定義のボタンIDです: {button_id}")
        if not isinstance(button, SceneButton):
            raise ConfigError("SwitchBotシーンだけを除外できます。")
        self.remove_buttons([button_id])
        return {
            "removed": True,
            "id": button.id,
            "label": button.label,
            "scene_id": button.scene_id,
            "excluded": True,
        }

    def restore_scene(self, scene_id: str) -> dict[str, Any]:
        config = load_config(self._config_path)
        if scene_id not in config.scene_sync.excluded_scene_ids:
            raise ConfigError("指定したシーンは除外されていません。")
        raw = config.model_dump()
        raw["scene_sync"]["excluded_scene_ids"] = [
            item for item in config.scene_sync.excluded_scene_ids if item != scene_id
        ]
        raw["scene_sync"]["excluded_scene_labels"].pop(scene_id, None)
        self._write(raw)
        return {"scene_id": scene_id, "excluded": False}

    def update_scene_sync(self, update: SceneSyncUpdate) -> dict[str, Any]:
        config = load_config(self._config_path)
        raw = config.model_dump()
        raw["scene_sync"]["auto_add"] = update.auto_add
        self._write(raw)
        return {"auto_add": update.auto_add}

    def save_remote_quick_action(self, update: RemoteQuickActionUpdate) -> dict[str, Any]:
        signature = f"{update.device_id}\0{update.command}\0{update.parameter}"
        button_id = f"remote_{hashlib.sha256(signature.encode()).hexdigest()[:12]}"
        config = load_config(self._config_path)
        group = update.group.strip()
        if group not in self._effective_quick_action_groups(config):
            raise ConfigError("先にクイック操作グループを追加してください。")
        existing = config.get_button(button_id)
        if existing is not None and not update.overwrite:
            raise ConfigError("同じリモコン設定が登録済みです。上書きする場合は確認してください。")

        item = RemoteCommandButton(
            id=button_id,
            label=update.label.strip(),
            group=group,
            type="remote_command",
            device_id=update.device_id,
            command=update.command,
            parameter=update.parameter,
            icon=update.icon,
            icon_badge=update.icon_badge,
        )
        raw = config.model_dump()
        raw["buttons"] = [button for button in raw["buttons"] if button["id"] != button_id]
        raw["buttons"].append(item.model_dump())
        self._write(raw)
        return {"id": button_id, "updated": existing is not None}

    def update_remote_quick_action(
        self, button_id: str, update: RemoteQuickActionUpdate
    ) -> dict[str, Any]:
        config = load_config(self._config_path)
        existing = config.get_button(button_id)
        if existing is None:
            raise ConfigError(f"未定義のボタンIDです: {button_id}")
        if not isinstance(existing, RemoteCommandButton):
            raise ConfigError("手動追加したリモコン操作だけを編集できます。")
        group = update.group.strip()
        if group not in self._effective_quick_action_groups(config):
            raise ConfigError("先にクイック操作グループを追加してください。")

        signature = f"{update.device_id}\0{update.command}\0{update.parameter}"
        new_id = f"remote_{hashlib.sha256(signature.encode()).hexdigest()[:12]}"
        duplicate = config.get_button(new_id)
        if duplicate is not None and duplicate.id != button_id:
            raise ConfigError("同じリモコン設定が別のクイック操作に登録済みです。")

        replacement = RemoteCommandButton(
            id=new_id,
            label=update.label.strip(),
            group=group,
            type="remote_command",
            device_id=update.device_id,
            command=update.command,
            parameter=update.parameter,
            locked=existing.locked,
            icon=update.icon,
            icon_badge=update.icon_badge,
        )
        raw = config.model_dump()
        raw["buttons"] = [
            replacement.model_dump() if item["id"] == button_id else item
            for item in raw["buttons"]
        ]
        self._write(raw)
        return {"id": new_id, "previous_id": button_id, "updated": True}

    def remove_remote_quick_action(self, button_id: str) -> dict[str, Any]:
        config = load_config(self._config_path)
        button = config.get_button(button_id)
        if button is None:
            raise ConfigError(f"未定義のボタンIDです: {button_id}")
        if not isinstance(button, RemoteCommandButton):
            raise ConfigError("手動追加したリモコン操作だけを削除できます。")
        raw = config.model_dump()
        raw["buttons"] = [item for item in raw["buttons"] if item["id"] != button_id]
        self._write(raw)
        return {"removed": True, "id": button_id, "label": button.label}

    def _write(self, raw: dict[str, Any]) -> None:
        validated = LauncherConfig.model_validate(raw)
        temporary_path = self._config_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(validated.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_path.replace(self._config_path)

    @staticmethod
    def _effective_quick_action_groups(config: LauncherConfig) -> list[str]:
        groups = list(dict.fromkeys(config.quick_action_groups))
        for button in config.buttons:
            if isinstance(button, SceneButton | RemoteCommandButton) and button.group not in groups:
                groups.append(button.group)
        if "シーン" not in groups:
            groups.append("シーン")
        return groups

    @staticmethod
    def _to_candidate(item: dict[str, Any]) -> ConfigCandidate:
        return ConfigCandidate(
            id=item["id"],
            label=item["label"],
            group=item.get("group", "その他"),
            type=item["type"],
            source_id=item.get("scene_id") or item.get("device_id"),
        )
