from __future__ import annotations

from typing import Dict

QWERTY_KEY_TO_SCAN: Dict[str, int] = {
    # Number row / punctuation
    '`': 41,
    '1': 2, '2': 3, '3': 4, '4': 5, '5': 6,
    '6': 7, '7': 8, '8': 9, '9': 10, '0': 11,
    '-': 12, '=': 13,
    # Letter rows
    'q': 16, 'w': 17, 'e': 18, 'r': 19, 't': 20,
    'y': 21, 'u': 22, 'i': 23, 'o': 24, 'p': 25,
    '[': 26, ']': 27,
    'a': 30, 's': 31, 'd': 32, 'f': 33, 'g': 34,
    'h': 35, 'j': 36, 'k': 37, 'l': 38, ';': 39, "'": 40, '\\': 43,
    'z': 44, 'x': 45, 'c': 46, 'v': 47, 'b': 48, 'n': 49, 'm': 50,
    ',': 51, '.': 52, '/': 53,
    # Special keys
    'tab': 15,
    'esc': 1,
    'space': 57,
    'enter': 28,
    'backspace': 14,
    'delete': 83,
    'insert': 82,
    'home': 71,
    'end': 79,
    'page_up': 73,
    'page_down': 81,
    'up': 72,
    'down': 80,
    'left': 75,
    'right': 77,
    # Function keys
    'f1': 59, 'f2': 60, 'f3': 61, 'f4': 62, 'f5': 63,
    'f6': 64, 'f7': 65, 'f8': 66, 'f9': 67, 'f10': 68,
    'f11': 87, 'f12': 88,
}

AZERTY_KEY_TO_SCAN: Dict[str, int] = {
    # Common French labels by physical key position
    '²': 41,
    '1': 2, '2': 3, '3': 4, '4': 5, '5': 6,
    '6': 7, '7': 8, '8': 9, '9': 10, '0': 11,
    ')': 12, '=': 13,
    # Letter rows
    'a': 16, 'z': 17, 'e': 18, 'r': 19, 't': 20,
    'y': 21, 'u': 22, 'i': 23, 'o': 24, 'p': 25,
    '^': 26, '$': 27,
    'q': 30, 's': 31, 'd': 32, 'f': 33, 'g': 34,
    'h': 35, 'j': 36, 'k': 37, 'l': 38, 'm': 39, 'ù': 40, '*': 43,
    'w': 44, 'x': 45, 'c': 46, 'v': 47, 'b': 48, 'n': 49, ',': 50,
    ';': 51, ':': 52, '!': 53,
    # Special keys
    'tab': 15,
    'esc': 1,
    'space': 57,
    'enter': 28,
    'backspace': 14,
    'delete': 83,
    'insert': 82,
    'home': 71,
    'end': 79,
    'page_up': 73,
    'page_down': 81,
    'up': 72,
    'down': 80,
    'left': 75,
    'right': 77,
    # Function keys
    'f1': 59, 'f2': 60, 'f3': 61, 'f4': 62, 'f5': 63,
    'f6': 64, 'f7': 65, 'f8': 66, 'f9': 67, 'f10': 68,
    'f11': 87, 'f12': 88,
}

LAYOUT_KEY_TO_SCAN = {
    'qwerty': QWERTY_KEY_TO_SCAN,
    'azerty': AZERTY_KEY_TO_SCAN,
}

# Backward-compatible aliases for code paths that still import these names.
KEY_TO_SCAN: Dict[str, int] = QWERTY_KEY_TO_SCAN
SCAN_TO_KEY: Dict[int, str] = {v: k for k, v in KEY_TO_SCAN.items()}

KEY_ALIASES = {
    'grave': '`',
    'backquote': '`',
    'tilde': '`',
    'return': 'enter',
    'escape': 'esc',
    'pgup': 'page_up',
    'pgdn': 'page_down',
    'del': 'delete',
    'ins': 'insert',
    'backslash': '\\',
}

HOTKEY_CONFIG_KEYS = [
    'prev_key', 'next_key', 'leader_key', 'sync_key', 'sync_right_key',
    'treasure_key', 'swap_xp_drop_key', 'toggle_app_key', 'paste_enter_key',
    'auto_zaap_key', 'refresh_key', 'calib_key', 'sort_taskbar_key',
    'invite_group_key', 'game_inv_key', 'game_char_key', 'game_spell_key',
    'game_haven_key', 'radial_menu_hotkey',
]

MODIFIER_TOKENS = {'ctrl', 'alt', 'shift'}
MOUSE_TOKENS = {'left_click', 'right_click', 'middle_click', 'mouse4', 'mouse5'}


def normalize_layout(layout: str | None) -> str:
    layout = (layout or 'qwerty').strip().lower()
    return layout if layout in LAYOUT_KEY_TO_SCAN else 'qwerty'


def get_key_to_scan(layout: str | None) -> Dict[str, int]:
    return LAYOUT_KEY_TO_SCAN[normalize_layout(layout)]


def get_scan_to_key(layout: str | None) -> Dict[int, str]:
    return {v: k for k, v in get_key_to_scan(layout).items()}


def normalize_key_name(key_name: str | None) -> str:
    if not key_name:
        return ''
    key_name = key_name.strip().lower()
    return KEY_ALIASES.get(key_name, key_name)


def get_scan_code_for_key(layout: str | None, key_name: str | None) -> int | None:
    key_name = normalize_key_name(key_name)
    if not key_name:
        return None
    layout_map = get_key_to_scan(layout)
    if key_name in layout_map:
        return layout_map[key_name]
    # Safe fallback for legacy configs / cross-layout transitions
    return QWERTY_KEY_TO_SCAN.get(key_name) or AZERTY_KEY_TO_SCAN.get(key_name)


def get_key_for_scan(layout: str | None, scan_code: int, fallback: str = '') -> str:
    return get_scan_to_key(layout).get(scan_code, fallback)


def convert_key_between_layouts(token: str, from_layout: str | None, to_layout: str | None) -> str:
    token = normalize_key_name(token)
    if not token:
        return ''
    if token in MODIFIER_TOKENS or token in MOUSE_TOKENS:
        return token
    scan = get_scan_code_for_key(from_layout, token)
    if scan is None:
        return token
    return get_key_for_scan(to_layout, scan, token)


def convert_hotkey_layout(hotkey: str | None, from_layout: str | None, to_layout: str | None) -> str:
    if not hotkey:
        return ''
    parts = [part for part in hotkey.split('+') if part]
    return '+'.join(convert_key_between_layouts(part, from_layout, to_layout) for part in parts)


def infer_layout_from_config(config_data: dict) -> str:
    explicit = normalize_layout(config_data.get('keyboard_layout'))
    if config_data.get('keyboard_layout'):
        return explicit

    sample_values = []
    for key in HOTKEY_CONFIG_KEYS:
        value = config_data.get(key)
        if isinstance(value, str) and value:
            sample_values.extend([normalize_key_name(p) for p in value.split('+') if p])

    if '²' in sample_values:
        return 'azerty'
    if config_data.get('next_key') == '²':
        return 'azerty'
    return 'qwerty'


def normalize_config_layout(config_data: dict) -> None:
    layout = infer_layout_from_config(config_data)
    config_data['keyboard_layout'] = layout

    for key in HOTKEY_CONFIG_KEYS:
        if key in config_data and isinstance(config_data.get(key), str):
            config_data[key] = '+'.join(normalize_key_name(part) for part in config_data[key].split('+') if part)

    row_binds = config_data.get('cycle_row_binds', [])
    if isinstance(row_binds, list):
        config_data['cycle_row_binds'] = [
            '+'.join(normalize_key_name(part) for part in str(v).split('+') if part)
            for v in row_binds
        ]

    char_binds = config_data.get('persistent_character_binds', {})
    if isinstance(char_binds, dict):
        config_data['persistent_character_binds'] = {
            pseudo: '+'.join(normalize_key_name(part) for part in str(bind).split('+') if part)
            for pseudo, bind in char_binds.items()
        }

    adv_mod = normalize_key_name(config_data.get("advanced_bind_modifier", "ctrl"))
    if adv_mod in {"", "none", "aucun", "nenhum"}:
        config_data["advanced_bind_modifier"] = "none"
    elif adv_mod in MODIFIER_TOKENS:
        config_data["advanced_bind_modifier"] = adv_mod
    else:
        config_data["advanced_bind_modifier"] = "ctrl"
