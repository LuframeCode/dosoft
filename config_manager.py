import json
import os

from keymap import normalize_config_layout


class Config:
    def __init__(self, filename="settings.json"):
        self.filename = filename
        self.data = {
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
                "ctrl+f1", "ctrl+f2", "ctrl+f3", "ctrl+f4",
                "ctrl+f5", "ctrl+f6", "ctrl+f7", "ctrl+f8"
            ],
        }
        self.load()

    def _normalize(self):
        self.data["language"] = (self.data.get("language") or "pt").strip().lower()
        if self.data["language"] not in {"pt", "en", "fr"}:
            self.data["language"] = "pt"
        mod = (self.data.get("advanced_bind_modifier") or "ctrl").strip().lower()
        if mod in {"", "none", "aucun", "nenhum"}:
            self.data["advanced_bind_modifier"] = "none"
        elif mod in {"ctrl", "alt", "shift"}:
            self.data["advanced_bind_modifier"] = mod
        else:
            self.data["advanced_bind_modifier"] = "ctrl"
        normalize_config_layout(self.data)

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data.update(loaded)
            except Exception:
                pass

        self._normalize()

    def save(self):
        self._normalize()
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def reset_settings(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
        self.__init__(self.filename)