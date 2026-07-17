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
        temporary_path = self._config_path.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary_path.replace(self._config_path)
        return preference

    def rooms(self) -> list[str]:
        return load_config(self._config_path).rooms

    def add_room(self, room: str) -> list[str]:
        room = room.strip()
        if not room:
            return self.rooms()
        config = load_config(self._config_path)
        raw = config.model_dump()
        if room not in raw["rooms"]:
            raw["rooms"].append(room)
            self._write(raw)
        return raw["rooms"]

    def reorder_rooms(self, rooms: list[str]) -> list[str]:
        config = load_config(self._config_path)
        if len(rooms) != len(set(rooms)) or set(rooms) != set(config.rooms):
            raise LauncherError("部屋の並び順が現在の部屋一覧と一致しません。")
        raw = config.model_dump()
        raw["rooms"] = rooms
        self._write(raw)
        return rooms

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
