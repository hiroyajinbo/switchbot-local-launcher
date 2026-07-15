import json
from pathlib import Path

from pydantic import BaseModel

from app.config import DevicePreference, LightPreset, load_config


class DevicePreferenceUpdate(BaseModel):
    room: str
    icon: str
    locked: bool


class LightPresetUpdate(BaseModel):
    name: str
    brightness: int | None = None
    color: str | None = None
    color_temperature: int | None = None


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

    def _write(self, raw: dict) -> None:
        temporary_path = self._config_path.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary_path.replace(self._config_path)
