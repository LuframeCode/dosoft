from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml


DEFAULT_LANGUAGE = "en"
DEFAULT_KEYBOARD_LAYOUT = "qwerty"


def _resolve_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


BASE_DIR = _resolve_base_dir()
LOCALES_DIR = BASE_DIR / "locales"


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_all_locales() -> dict[str, dict[str, Any]]:
    locales: dict[str, dict[str, Any]] = {}
    for code in ("pt", "en", "fr"):
        locales[code] = _load_yaml_file(LOCALES_DIR / f"{code}.yml")
    return locales


_LOCALES = _load_all_locales()


def _normalize_lang(value: Any) -> str:
    lang = str(value or DEFAULT_LANGUAGE).strip().lower()
    return lang if lang in _LOCALES else DEFAULT_LANGUAGE


def _extract_lang(config_or_lang: Any) -> str:
    if hasattr(config_or_lang, "data"):
        return _normalize_lang(config_or_lang.data.get("language", DEFAULT_LANGUAGE))
    if isinstance(config_or_lang, dict):
        return _normalize_lang(config_or_lang.get("language", DEFAULT_LANGUAGE))
    return _normalize_lang(config_or_lang)


def _locale_section(lang: str) -> dict[str, Any]:
    return _LOCALES.get(lang, _LOCALES.get(DEFAULT_LANGUAGE, {}))


def _meta(lang: str) -> dict[str, Any]:
    meta = _locale_section(lang).get("meta", {})
    return meta if isinstance(meta, dict) else {}


def _translations(lang: str) -> dict[str, str]:
    data = _locale_section(lang).get("translations", {})
    return data if isinstance(data, dict) else {}


def _normalize_label(value: str | None) -> str:
    return (value or "").strip().lower()


def reload_locales() -> None:
    global _LOCALES
    _LOCALES = _load_all_locales()


def get_language_from_settings(settings_path: str = "settings.json") -> str:
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return _normalize_lang(data.get("language", DEFAULT_LANGUAGE))
        except Exception:
            pass
    return DEFAULT_LANGUAGE


def tr(config_or_lang: Any, text: str, **kwargs) -> str:
    lang = _extract_lang(config_or_lang)
    translated = _translations(lang).get(text, text)

    if kwargs:
        try:
            return translated.format(**kwargs)
        except Exception:
            return translated

    return translated


LANGUAGE_LABELS = {
    "pt": {
        "pt": "Português",
        "en": "Portuguese",
        "fr": "Portugais",
    },
    "en": {
        "pt": "Inglês",
        "en": "English",
        "fr": "Anglais",
    },
    "fr": {
        "pt": "Francês",
        "en": "French",
        "fr": "Français",
    },
}


def get_language_options(ui_lang: str | None = None) -> list[str]:
    ui_lang = _normalize_lang(ui_lang or DEFAULT_LANGUAGE)
    return [LANGUAGE_LABELS["fr"][ui_lang], LANGUAGE_LABELS["en"][ui_lang], LANGUAGE_LABELS["pt"][ui_lang]]


def language_code_from_label(label: str) -> str:
    normalized = _normalize_label(label)

    for code, labels in LANGUAGE_LABELS.items():
        if normalized == code:
            return code
        if normalized in {
            labels["fr"].lower(),
            labels["pt"].lower(),
            labels["en"].lower(),
            
        }:
            return code

    return DEFAULT_LANGUAGE


def language_label(code: str, ui_lang: str | None = None) -> str:
    code = _normalize_lang(code)
    ui_lang = _normalize_lang(ui_lang or DEFAULT_LANGUAGE)
    return LANGUAGE_LABELS.get(code, LANGUAGE_LABELS[DEFAULT_LANGUAGE])[ui_lang]


KEYBOARD_LAYOUT_LABELS = {
    "qwerty": {
        "pt": "QWERTY",
        "en": "QWERTY",
        "fr": "QWERTY",
    },
    "azerty": {
        "pt": "AZERTY",
        "en": "AZERTY",
        "fr": "AZERTY",
    },
}


def get_keyboard_layout_options(ui_lang: str | None = None) -> list[str]:
    ui_lang = _normalize_lang(ui_lang or DEFAULT_LANGUAGE)
    return [
        KEYBOARD_LAYOUT_LABELS["qwerty"][ui_lang],
        KEYBOARD_LAYOUT_LABELS["azerty"][ui_lang],
    ]


def keyboard_layout_from_label(label: str) -> str:
    normalized = _normalize_label(label)

    for code, labels in KEYBOARD_LAYOUT_LABELS.items():
        if normalized == code:
            return code
        if normalized in {
            labels["pt"].lower(),
            labels["en"].lower(),
            labels["fr"].lower(),
        }:
            return code

    return DEFAULT_KEYBOARD_LAYOUT


def keyboard_layout_label(ui_lang: str, code: str) -> str:
    ui_lang = _normalize_lang(ui_lang or DEFAULT_LANGUAGE)
    code = str(code or DEFAULT_KEYBOARD_LAYOUT).strip().lower()
    if code not in KEYBOARD_LAYOUT_LABELS:
        code = DEFAULT_KEYBOARD_LAYOUT
    return KEYBOARD_LAYOUT_LABELS[code][ui_lang]


def get_meta_value(config_or_lang: Any, key: str, default: Any = None) -> Any:
    lang = _extract_lang(config_or_lang)
    return _meta(lang).get(key, default)