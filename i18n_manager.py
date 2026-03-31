import json
import os
import sys
from typing import Any, Dict


class I18nManager:
    def __init__(self, locale: str, base_path: str = "resources/i18n"):
        self.base_path = self._resolve_base_path(base_path)
        self.default_locale = "fr"
        self.locale = locale or self.default_locale
        self.default_strings = self._load_locale_file(self.default_locale)
        self.current_strings = self._load_locale_file(self.locale)

    def _resolve_base_path(self, relative_path: str) -> str:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, relative_path)
        return relative_path

    def _load_locale_file(self, locale: str) -> Dict[str, Any]:
        file_path = os.path.join(self.base_path, f"{locale}.yml")
        if not os.path.exists(file_path):
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as stream:
                return json.load(stream)
        except Exception:
            return {}

    def set_locale(self, locale: str) -> None:
        self.locale = locale or self.default_locale
        self.current_strings = self._load_locale_file(self.locale)

    def t(self, key: str, default: str = "") -> str:
        if key in self.current_strings:
            return str(self.current_strings[key])
        if key in self.default_strings:
            return str(self.default_strings[key])
        return default or key
