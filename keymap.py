from __future__ import annotations

from typing import Dict


# ============================================================
# Teclas comuns por posição física (scan code)
# Estas praticamente não mudam entre layouts.
# ============================================================

COMMON_SCAN_TO_KEY: Dict[int, str] = {
    # Special keys
    1: "esc",
    14: "backspace",
    15: "tab",
    28: "enter",
    57: "space",
    71: "home",
    72: "up",
    73: "page_up",
    75: "left",
    77: "right",
    79: "end",
    80: "down",
    81: "page_down",
    82: "insert",
    83: "delete",

    # Function keys
    59: "f1",
    60: "f2",
    61: "f3",
    62: "f4",
    63: "f5",
    64: "f6",
    65: "f7",
    66: "f8",
    67: "f9",
    68: "f10",
    87: "f11",
    88: "f12",
}


# ============================================================
# Layouts
# Cada layout define apenas as teclas variáveis por posição.
# Para adicionar outro layout, basta adicionar outro bloco.
# ============================================================

LAYOUTS: Dict[str, Dict[int, str]] = {
    "qwerty": {
        41: "`",
        2: "1", 3: "2", 4: "3", 5: "4", 6: "5",
        7: "6", 8: "7", 9: "8", 10: "9", 11: "0",
        12: "-", 13: "=",

        16: "q", 17: "w", 18: "e", 19: "r", 20: "t",
        21: "y", 22: "u", 23: "i", 24: "o", 25: "p",
        26: "[", 27: "]",

        30: "a", 31: "s", 32: "d", 33: "f", 34: "g",
        35: "h", 36: "j", 37: "k", 38: "l", 39: ";",
        40: "'", 43: "\\",

        44: "z", 45: "x", 46: "c", 47: "v", 48: "b",
        49: "n", 50: "m", 51: ",", 52: ".", 53: "/",
    },
    "azerty": {
        41: "²",
        2: "1", 3: "2", 4: "3", 5: "4", 6: "5",
        7: "6", 8: "7", 9: "8", 10: "9", 11: "0",
        12: ")", 13: "=",

        16: "a", 17: "z", 18: "e", 19: "r", 20: "t",
        21: "y", 22: "u", 23: "i", 24: "o", 25: "p",
        26: "^", 27: "$",

        30: "q", 31: "s", 32: "d", 33: "f", 34: "g",
        35: "h", 36: "j", 37: "k", 38: "l", 39: "m",
        40: "ù", 43: "*",

        44: "w", 45: "x", 46: "c", 47: "v", 48: "b",
        49: "n", 50: ",", 51: ";", 52: ":", 53: "!",
    },

    # EXEMPLO para adicionar outro layout depois:
    # "abnt2": {
    #     41: "'",
    #     2: "1", 3: "2", ...
    # }
}


DEFAULT_LAYOUT = "qwerty"


KEY_ALIASES = {
    "grave": "`",
    "backquote": "`",
    "tilde": "`",
    "return": "enter",
    "escape": "esc",
    "pgup": "page_up",
    "pgdn": "page_down",
    "del": "delete",
    "ins": "insert",
    "backslash": "\\",
}


HOTKEY_CONFIG_KEYS = [
    "prev_key",
    "next_key",
    "leader_key",
    "sync_key",
    "sync_right_key",
    "treasure_key",
    "swap_xp_drop_key",
    "toggle_app_key",
    "paste_enter_key",
    "auto_zaap_key",
    "refresh_key",
    "calib_key",
    "sort_taskbar_key",
    "invite_group_key",
    "game_inv_key",
    "game_char_key",
    "game_spell_key",
    "game_haven_key",
    "radial_menu_hotkey",
]

MODIFIER_TOKENS = {"ctrl", "alt", "shift"}
MOUSE_TOKENS = {"left_click", "right_click", "middle_click", "mouse4", "mouse5"}



def _build_scan_to_key(layout: str) -> Dict[int, str]:
    base = dict(COMMON_SCAN_TO_KEY)
    base.update(LAYOUTS[layout])
    return base


def _build_key_to_scan(layout: str) -> Dict[str, int]:
    scan_to_key = _build_scan_to_key(layout)
    return {key: scan for scan, key in scan_to_key.items()}


KEY_TO_SCAN: Dict[str, int] = _build_key_to_scan(DEFAULT_LAYOUT)
SCAN_TO_KEY: Dict[int, str] = _build_scan_to_key(DEFAULT_LAYOUT)



def normalize_layout(layout: str | None) -> str:
    layout = (layout or DEFAULT_LAYOUT).strip().lower()
    return layout if layout in LAYOUTS else DEFAULT_LAYOUT


def normalize_key_name(key_name: str | None) -> str:
    if not key_name:
        return ""
    key_name = str(key_name).strip().lower()
    return KEY_ALIASES.get(key_name, key_name)


def normalize_hotkey(hotkey: str | None) -> str:
    if not hotkey:
        return ""
    parts = [normalize_key_name(part) for part in str(hotkey).split("+") if part]
    return "+".join(parts)



def get_scan_to_key(layout: str | None) -> Dict[int, str]:
    return _build_scan_to_key(normalize_layout(layout))


def get_key_to_scan(layout: str | None) -> Dict[str, int]:
    return _build_key_to_scan(normalize_layout(layout))


def available_layouts() -> list[str]:
    return list(LAYOUTS.keys())



def get_scan_code_for_key(layout: str | None, key_name: str | None) -> int | None:
    key_name = normalize_key_name(key_name)
    if not key_name:
        return None

    layout_map = get_key_to_scan(layout)
    if key_name in layout_map:
        return layout_map[key_name]

    # fallback cruzado: tenta achar em qualquer layout conhecido
    for layout_name in available_layouts():
        fallback_map = get_key_to_scan(layout_name)
        if key_name in fallback_map:
            return fallback_map[key_name]

    return None


def get_key_for_scan(layout: str | None, scan_code: int, fallback: str = "") -> str:
    return get_scan_to_key(layout).get(scan_code, fallback)



def convert_key_between_layouts(token: str, from_layout: str | None, to_layout: str | None) -> str:
    token = normalize_key_name(token)
    if not token:
        return ""

    if token in MODIFIER_TOKENS or token in MOUSE_TOKENS:
        return token

    scan = get_scan_code_for_key(from_layout, token)
    if scan is None:
        return token

    return get_key_for_scan(to_layout, scan, token)


def convert_hotkey_layout(hotkey: str | None, from_layout: str | None, to_layout: str | None) -> str:
    if not hotkey:
        return ""

    parts = [part for part in str(hotkey).split("+") if part]
    converted = [convert_key_between_layouts(part, from_layout, to_layout) for part in parts]
    return "+".join(converted)


def infer_layout_from_config(config_data: dict) -> str:
    explicit = normalize_layout(config_data.get("keyboard_layout"))
    if config_data.get("keyboard_layout"):
        return explicit

    sample_values = []

    for key in HOTKEY_CONFIG_KEYS:
        value = config_data.get(key)
        if isinstance(value, str) and value:
            sample_values.extend(normalize_key_name(part) for part in value.split("+") if part)

    row_binds = config_data.get("cycle_row_binds", [])
    if isinstance(row_binds, list):
        for value in row_binds:
            if value:
                sample_values.extend(normalize_key_name(part) for part in str(value).split("+") if part)

    char_binds = config_data.get("persistent_character_binds", {})
    if isinstance(char_binds, dict):
        for value in char_binds.values():
            if value:
                sample_values.extend(normalize_key_name(part) for part in str(value).split("+") if part)

    # heurística simples e extensível
    if "²" in sample_values or config_data.get("next_key") == "²":
        return "azerty"

    return DEFAULT_LAYOUT



def normalize_config_layout(config_data: dict) -> None:
    layout = infer_layout_from_config(config_data)
    config_data["keyboard_layout"] = layout

    for key in HOTKEY_CONFIG_KEYS:
        if key in config_data and isinstance(config_data.get(key), str):
            config_data[key] = normalize_hotkey(config_data[key])

    row_binds = config_data.get("cycle_row_binds", [])
    if isinstance(row_binds, list):
        config_data["cycle_row_binds"] = [
            normalize_hotkey(value) for value in row_binds
        ]

    char_binds = config_data.get("persistent_character_binds", {})
    if isinstance(char_binds, dict):
        config_data["persistent_character_binds"] = {
            pseudo: normalize_hotkey(bind)
            for pseudo, bind in char_binds.items()
        }

    adv_mod = normalize_key_name(config_data.get("advanced_bind_modifier", "ctrl"))
    if adv_mod in {"", "none", "aucun", "nenhum"}:
        config_data["advanced_bind_modifier"] = "none"
    elif adv_mod in MODIFIER_TOKENS:
        config_data["advanced_bind_modifier"] = adv_mod
    else:
        config_data["advanced_bind_modifier"] = "ctrl"