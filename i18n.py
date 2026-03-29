from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_LANGUAGE = "en"
DEFAULT_SPEED = "fast" #still need this ? 
DEFAULT_KEYBOARD_LAYOUT = "qwerty"

BASE_DIR = Path(__file__).resolve().parent
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


def _locale_section(lang: str) -> dict[str, Any]:
    return _LOCALES.get(lang, _LOCALES.get(DEFAULT_LANGUAGE, {}))


def _meta(lang: str) -> dict[str, Any]:
    return _locale_section(lang).get("meta", {})


def _translations(lang: str) -> dict[str, str]:
    data = _locale_section(lang).get("translations", {})
    return data if isinstance(data, dict) else {}


def _normalize_lang(value: Any) -> str:
    lang = str(value or DEFAULT_LANGUAGE).strip().lower()
    return lang if lang in _LOCALES else DEFAULT_LANGUAGE


def _extract_lang(config_or_lang: Any) -> str:
    if hasattr(config_or_lang, "data"):
        return _normalize_lang(config_or_lang.data.get("language", DEFAULT_LANGUAGE))
    if isinstance(config_or_lang, dict):
        return _normalize_lang(config_or_lang.get("language", DEFAULT_LANGUAGE))
    return _normalize_lang(config_or_lang)


def _normalize_label(value: str | None) -> str:
    return (value or "").strip().lower()



def get_language_from_settings(settings_path: str = "settings.json") -> str:
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
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
    return [
        LANGUAGE_LABELS["fr"][ui_lang],
        LANGUAGE_LABELS["pt"][ui_lang],
        LANGUAGE_LABELS["en"][ui_lang],
        
    ]

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


def _speed_labels(lang: str) -> dict[str, str]:
    labels = _meta(lang).get("speed_labels", {})
    return labels if isinstance(labels, dict) else {}


def _legacy_speed_values() -> dict[str, str]:
    result: dict[str, str] = {}
    for code in _LOCALES:
        mapping = _meta(code).get("legacy_speed_values", {})
        if isinstance(mapping, dict):
            for k, v in mapping.items():
                result[str(k).strip().lower()] = str(v).strip().lower()
    return result


def normalize_speed_value(value: str | None) -> str:
    normalized = _normalize_label(value)
    return _legacy_speed_values().get(normalized, DEFAULT_SPEED)


def speed_label(lang: str, value: str) -> str:
    lang = _normalize_lang(lang)
    value = normalize_speed_value(value)
    labels = _speed_labels(lang)
    if value in labels:
        return labels[value]
    fallback = _speed_labels(DEFAULT_LANGUAGE)
    return fallback.get(value, value)


def get_speed_options(lang: str) -> list[str]:
    return [
        speed_label(lang, "fast"),
        speed_label(lang, "medium"),
        speed_label(lang, "slow"),
    ]


def speed_value_from_label(label: str) -> str:
    normalized = _normalize_label(label)
    for code in _LOCALES:
        labels = _speed_labels(code)
        for value, text in labels.items():
            if normalized == str(text).strip().lower():
                return value
    return normalize_speed_value(label)


def _keyboard_layout_labels(lang: str) -> dict[str, str]:
    labels = _meta(lang).get("keyboard_layout_labels", {})
    return labels if isinstance(labels, dict) else {}


def keyboard_layout_label(lang: str, layout: str) -> str:
    lang = _normalize_lang(lang)
    layout = _normalize_label(layout) or DEFAULT_KEYBOARD_LAYOUT
    labels = _keyboard_layout_labels(lang)
    if layout in labels:
        return labels[layout]
    fallback = _keyboard_layout_labels(DEFAULT_LANGUAGE)
    return fallback.get(layout, layout)


def get_keyboard_layout_options(lang: str) -> list[str]:
    return [
        keyboard_layout_label(lang, "qwerty"),
        keyboard_layout_label(lang, "azerty"),
    ]


def keyboard_layout_from_label(label: str) -> str:
    normalized = _normalize_label(label)
    for code in _LOCALES:
        labels = _keyboard_layout_labels(code)
        for layout, text in labels.items():
            if normalized == str(text).strip().lower():
                return layout
    return DEFAULT_KEYBOARD_LAYOUT