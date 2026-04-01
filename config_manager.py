import json
import os

class Config:
    def __init__(self, filename="settings.json"):
        self.filename = filename
        self.data = {
            "prev_key": "tab",
            "next_key": "²",
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
            # --- NOUVEAU : Gestionnaire de Binds Avancé DOSOFT ---
            "advanced_bind_mode": "cycle", 
            "advanced_bind_modifier": "ctrl",
            "persistent_character_binds": {}, 
            "cycle_row_binds": ["ctrl+F1", "ctrl+F2", "ctrl+F3", "ctrl+F4", "ctrl+F5", "ctrl+F6", "ctrl+F7", "ctrl+F8"],
            "keyboard_layout": "azerty_fr",
            "language": "fr"
        }
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception: pass

    def save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception: pass
            
    def reset_settings(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
        self.__init__(self.filename)