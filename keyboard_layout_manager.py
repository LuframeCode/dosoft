import json
import os
import sys
from typing import Dict, Optional

import keyboard


class KeyboardLayoutManager:
    def __init__(self, layout_name: str, base_path: str = "resources/keyboards"):
        self.base_path = self._resolve_base_path(base_path)
        self.default_layout = "azerty_fr"
        self.layout_name = layout_name or self.default_layout
        self.layout_map = self._load_layout(self.layout_name)
        self.scan_to_key = {scan: key for key, scan in self.layout_map.items()}

    def _resolve_base_path(self, relative_path: str) -> str:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, relative_path)
        return relative_path

    def _load_layout(self, layout_name: str) -> Dict[str, int]:
        file_path = os.path.join(self.base_path, f"{layout_name}.yml")
        if not os.path.exists(file_path):
            file_path = os.path.join(self.base_path, f"{self.default_layout}.yml")

        try:
            with open(file_path, "r", encoding="utf-8") as stream:
                data = json.load(stream)
        except Exception:
            data = {}

        keys = data.get("keys", {})
        normalized = {}
        for key, value in keys.items():
            try:
                normalized[str(key).lower().strip()] = int(value)
            except Exception:
                continue
        return normalized

    def set_layout(self, layout_name: str) -> None:
        self.layout_name = layout_name or self.default_layout
        self.layout_map = self._load_layout(self.layout_name)
        self.scan_to_key = {scan: key for key, scan in self.layout_map.items()}

    def key_to_scan(self, key_name: str) -> Optional[int]:
        if not key_name:
            return None
        return self.layout_map.get(key_name.lower().strip())

    def scan_to_key_name(self, scan_code: int) -> Optional[str]:
        return self.scan_to_key.get(scan_code)

    def resolve_scan_code(self, token: str) -> Optional[int]:
        scan = self.key_to_scan(token)
        if scan is not None:
            return scan
        try:
            return keyboard.key_to_scan_codes(token)[0]
        except Exception:
            return None
