from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from keymap import normalize_config_layout


DEFAULT_CONFIG: dict[str, Any] = {
    "language": "fr",
    "keyboard_layout": "qwerty",
    "prev_key": "tab",
    "next_key": "`",
    "leader_key": "f1",
    "toggle_app_key": "f10",
    "leader_name": "",
    "accounts_state": {},
    "accounts_team": {},
    "current_mode": "ALL",
    "classes": {},
    "custom_order": [],
    "show_tooltips": True,
    "volume_level": 50,
    "tutorial_done": False,
    "radial_menu_active": True,
    "radial_menu_hotkey": "alt+left_click",
    "game_version": "Unity",
    "ignore_organizer_warning": False,
    "auto_focus_retro": False,
    "advanced_bind_mode": "cycle",
    "advanced_bind_modifier": "none",
    "persistent_character_binds": {},
    "cycle_row_binds": [
        "ctrl+f1",
        "ctrl+f2",
        "ctrl+f3",
        "ctrl+f4",
        "ctrl+f5",
        "ctrl+f6",
        "ctrl+f7",
        "ctrl+f8",
    ],
}


class Config:
    def __init__(self, filename: str = "settings.json"):
        self.path = Path(filename)
        self.filename = str(self.path)  # compatibilidade com código antigo
        self.data: dict[str, Any] = self._fresh_defaults()
        self._last_saved_snapshot: str = ""
        self.load()

    def _fresh_defaults(self) -> dict[str, Any]:
        return copy.deepcopy(DEFAULT_CONFIG)

    def _snapshot(self) -> str:
        try:
            return json.dumps(self.data, ensure_ascii=False, sort_keys=True)
        except Exception:
            return ""

    def _normalize_language(self) -> None:
        lang = str(self.data.get("language") or DEFAULT_CONFIG["language"]).strip().lower()
        self.data["language"] = lang if lang in {"pt", "en", "fr"} else DEFAULT_CONFIG["language"]

    def _normalize_modifier(self) -> None:
        mod = str(self.data.get("advanced_bind_modifier") or "none").strip().lower()
        if mod in {"", "none", "aucun", "nenhum"}:
            self.data["advanced_bind_modifier"] = "none"
        elif mod in {"ctrl", "alt", "shift"}:
            self.data["advanced_bind_modifier"] = mod
        else:
            self.data["advanced_bind_modifier"] = "ctrl"

    def _normalize_scalar_defaults(self) -> None:
        if not isinstance(self.data.get("leader_name"), str):
            self.data["leader_name"] = ""

        if self.data.get("current_mode") not in {"ALL", "Team 1", "Team 2"}:
            self.data["current_mode"] = "ALL"

        if self.data.get("game_version") not in {"Unity", "Rétro"}:
            self.data["game_version"] = "Unity"

        try:
            volume = int(self.data.get("volume_level", DEFAULT_CONFIG["volume_level"]))
        except Exception:
            volume = DEFAULT_CONFIG["volume_level"]
        self.data["volume_level"] = max(0, min(100, volume))

        for key in (
            "show_tooltips",
            "tutorial_done",
            "radial_menu_active",
            "ignore_organizer_warning",
            "auto_focus_retro",
        ):
            self.data[key] = bool(self.data.get(key, DEFAULT_CONFIG[key]))

        mode = str(self.data.get("advanced_bind_mode") or DEFAULT_CONFIG["advanced_bind_mode"]).strip().lower()
        self.data["advanced_bind_mode"] = mode if mode in {"cycle", "bind"} else DEFAULT_CONFIG["advanced_bind_mode"]

    def _normalize_collection_defaults(self) -> None:
        if not isinstance(self.data.get("accounts_state"), dict):
            self.data["accounts_state"] = {}
        if not isinstance(self.data.get("accounts_team"), dict):
            self.data["accounts_team"] = {}
        if not isinstance(self.data.get("classes"), dict):
            self.data["classes"] = {}
        if not isinstance(self.data.get("custom_order"), list):
            self.data["custom_order"] = []
        if not isinstance(self.data.get("persistent_character_binds"), dict):
            self.data["persistent_character_binds"] = {}

        row_binds = self.data.get("cycle_row_binds")
        if not isinstance(row_binds, list):
            row_binds = copy.deepcopy(DEFAULT_CONFIG["cycle_row_binds"])

        normalized_rows = [str(v) if v is not None else "" for v in row_binds[:8]]
        while len(normalized_rows) < 8:
            normalized_rows.append(copy.deepcopy(DEFAULT_CONFIG["cycle_row_binds"])[len(normalized_rows)])
        self.data["cycle_row_binds"] = normalized_rows

    def _normalize(self) -> None:
        merged = self._fresh_defaults()
        if isinstance(self.data, dict):
            merged.update(self.data)
        self.data = merged

        self._normalize_language()
        self._normalize_modifier()
        self._normalize_scalar_defaults()
        self._normalize_collection_defaults()
        normalize_config_layout(self.data)

    def load(self) -> None:
        loaded: dict[str, Any] = {}
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as f:
                    parsed = json.load(f)
                if isinstance(parsed, dict):
                    loaded = parsed
            except Exception:
                loaded = {}

        self.data = self._fresh_defaults()
        self.data.update(loaded)
        self._normalize()
        self._last_saved_snapshot = self._snapshot()

    def reload(self) -> None:
        self.load()

    def save(self, force: bool = False) -> bool:
        self._normalize()
        new_snapshot = self._snapshot()

        if not force and new_snapshot == self._last_saved_snapshot:
            return False

        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, self.path)
            self._last_saved_snapshot = new_snapshot
            return True
        except Exception:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            return False

    def update(self, **changes: Any) -> bool:
        self.data.update(changes)
        return self.save()

    def reset_settings(self) -> None:
        try:
            if self.path.exists():
                self.path.unlink()
        except Exception:
            pass

        self.data = self._fresh_defaults()
        self._normalize()
        self.save(force=True)

    def mark_dirty(self) -> None:
        self._last_saved_snapshot = ""

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self.data)