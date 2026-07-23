import json
from pathlib import Path

from pydantic import BaseModel

from app.config import DevicePreference, LightPreset, load_config
from app.errors import LauncherError


class DevicePreferenceUpdate(BaseModel):
    room: str
    icon: str
    locked: bool


class LightPresetUpdate(BaseModel):
    name: str
    brightness: int | None = None
    color: str | None = None
    color_temperature: int | None = None


class RoomOrderUpdate(BaseModel):
    rooms: list[str]


class DevicePreferenceService:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path

    def update(self, device_id: str, update: DevicePreferenceUpdate) -> DevicePreference:
        preference = DevicePreference.model_validate(update.model_dump())
        config = load_config(self._config_path)
        raw = config.model_dump()
        raw["device_preferences"][device_id] = preference.model_dump()
        if preference.room not in raw["rooms"]:
            raw["rooms"].append(preference.room)
        temporary_path = self._config_path.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary_path.replace(self._config_path)
        return preference

    def rooms(self) -> list[str]:
        return self._effective_rooms(load_config(self._config_path))

    def add_room(self, room: str) -> list[str]:
        room = room.strip()
        if not room:
            return self.rooms()
        config = load_config(self._config_path)
        raw = config.model_dump()
        raw["rooms"] = self._effective_rooms(config)
        if room not in raw["rooms"]:
            raw["rooms"].append(room)
            self._write(raw)
        return raw["rooms"]

    def reorder_rooms(self, rooms: list[str]) -> list[str]:
        config = load_config(self._config_path)
        if len(rooms) != len(set(rooms)) or set(rooms) != set(self._effective_rooms(config)):
            raise LauncherError("部屋の並び順が現在の部屋一覧と一致しません。")
        raw = config.model_dump()
        raw["rooms"] = rooms
        self._write(raw)
        return rooms

    def remove_room(self, room: str) -> dict[str, object]:
        room = room.strip()
        if room == "未分類":
            raise LauncherError("「未分類」は削除できません。")

        config = load_config(self._config_path)
        if room not in self._effective_rooms(config):
            raise LauncherError("削除する部屋が見つかりません。")

        raw = config.model_dump()
        moved = 0
        for preference in raw["device_preferences"].values():
            if preference["room"] == room:
                preference["room"] = "未分類"
                moved += 1

        raw["rooms"] = [item for item in raw["rooms"] if item != room]
        if "未分類" not in raw["rooms"]:
            raw["rooms"].append("未分類")
        self._write(raw)
        return {"removed": room, "moved_devices": moved, "rooms": raw["rooms"]}

    def excluded_devices(self) -> list[dict[str, str]]:
        config = load_config(self._config_path)
        return [
            {"device_id": device_id, "label": label}
            for device_id, label in config.excluded_devices.items()
        ]

    def exclude_device(self, device_id: str, label: str) -> dict[str, object]:
        device_id = device_id.strip()
        if not device_id:
            raise LauncherError("非表示にするデバイスIDがありません。")
        config = load_config(self._config_path)
        raw = config.model_dump()
        raw["excluded_devices"][device_id] = label.strip() or device_id
        self._write(raw)
        return {"excluded": True, "devices": self.excluded_devices()}

    def restore_device(self, device_id: str) -> dict[str, object]:
        config = load_config(self._config_path)
        if device_id not in config.excluded_devices:
            raise LauncherError("非表示デバイスが見つかりません。")
        raw = config.model_dump()
        label = raw["excluded_devices"].pop(device_id)
        self._write(raw)
        return {
            "excluded": False,
            "device_id": device_id,
            "label": label,
            "devices": self.excluded_devices(),
        }

    def add_preset(self, device_id: str, update: LightPresetUpdate) -> LightPreset:
        preset = LightPreset.model_validate(update.model_dump())
        config = load_config(self._config_path)
        raw = config.model_dump()
        presets = raw["light_presets"].setdefault(device_id, [])
        presets[:] = [item for item in presets if item["name"] != preset.name]
        presets.append(preset.model_dump())
        self._write(raw)
        return preset

    def remove_preset(self, device_id: str, name: str) -> bool:
        config = load_config(self._config_path)
        raw = config.model_dump()
        presets = raw["light_presets"].get(device_id, [])
        remaining = [item for item in presets if item["name"] != name]
        if len(remaining) == len(presets):
            return False
        if remaining:
            raw["light_presets"][device_id] = remaining
        else:
            raw["light_presets"].pop(device_id, None)
        self._write(raw)
        return True

    def update_preset(
        self, device_id: str, current_name: str, update: LightPresetUpdate
    ) -> LightPreset:
        preset = LightPreset.model_validate(update.model_dump())
        config = load_config(self._config_path)
        raw = config.model_dump()
        presets = raw["light_presets"].get(device_id, [])
        index = next(
            (position for position, item in enumerate(presets) if item["name"] == current_name),
            None,
        )
        if index is None:
            raise LauncherError("編集するマイセットが見つかりません。")
        if preset.name != current_name and any(item["name"] == preset.name for item in presets):
            raise LauncherError("同じ名前のマイセットがすでにあります。")
        presets[index] = preset.model_dump()
        self._write(raw)
        return preset

    def _write(self, raw: dict) -> None:
        temporary_path = self._config_path.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary_path.replace(self._config_path)

    @staticmethod
    def _effective_rooms(config) -> list[str]:
        rooms = list(config.rooms)
        for preference in config.device_preferences.values():
            if preference.room not in rooms:
                rooms.append(preference.room)
        return rooms
