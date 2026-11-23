"""Correspondance entre les scan codes PC (set 1) et les keycodes virtuels macOS.

Les fichiers resources/keyboards/*.yml décrivent les touches avec leurs scan
codes PC. Les keycodes macOS (kVK_*) sont eux aussi positionnels, ce qui
permet de réutiliser tels quels ces fichiers de disposition (AZERTY, QWERTY…)
et les raccourcis déjà enregistrés dans settings.json.

Les touches « étendues » PC (flèches, Inser, Suppr…) partagent leur scan code
avec le pavé numérique ; elles reçoivent ici des pseudo scan codes 0xE0xx.
"""

# scan code PC -> keycode(s) macOS
SCAN_TO_MAC = {
    1: [53],            # esc
    2: [18], 3: [19], 4: [20], 5: [21], 6: [23], 7: [22], 8: [26], 9: [28], 10: [25], 11: [29],
    12: [27],           # - )
    13: [24],           # = +
    14: [51],           # backspace
    15: [48],           # tab
    16: [12], 17: [13], 18: [14], 19: [15], 20: [17], 21: [16], 22: [32], 23: [34], 24: [31], 25: [35],
    26: [33], 27: [30],
    28: [36],           # enter
    29: [59],           # left ctrl
    30: [0], 31: [1], 32: [2], 33: [3], 34: [5], 35: [4], 36: [38], 37: [40], 38: [37],
    39: [41], 40: [39],
    # Touche en haut à gauche (² / ` / @) : selon le clavier Mac (ISO/ANSI) elle
    # remonte en kVK_ISO_Section (10) ou kVK_ANSI_Grave (50).
    41: [10, 50],
    42: [56],           # left shift
    43: [42],           # \ *
    44: [6], 45: [7], 46: [8], 47: [9], 48: [11], 49: [45], 50: [46],
    51: [43], 52: [47], 53: [44],
    54: [60],           # right shift
    55: [67],           # num *
    56: [58],           # left alt / option
    57: [49],           # space
    58: [57],           # caps lock
    59: [122], 60: [120], 61: [99], 62: [118], 63: [96], 64: [97], 65: [98], 66: [100], 67: [101], 68: [109],
    69: [71],           # num lock / clear
    71: [89], 72: [91], 73: [92], 74: [78], 75: [86], 76: [87], 77: [88], 78: [69],
    79: [83], 80: [84], 81: [85], 82: [82], 83: [65],
    87: [103], 88: [111],                      # f11 f12
    100: [105], 101: [107], 102: [113], 103: [106], 104: [64], 105: [79], 106: [80], 107: [90],  # f13-f20
    # Touches étendues (pseudo scan codes)
    0xE01C: [76],       # num enter
    0xE01D: [62],       # right ctrl
    0xE035: [75],       # num /
    0xE038: [61],       # right alt / option
    0xE047: [115],      # home
    0xE048: [126],      # up
    0xE049: [116],      # page up
    0xE04B: [123],      # left
    0xE04D: [124],      # right
    0xE04F: [119],      # end
    0xE050: [125],      # down
    0xE051: [121],      # page down
    0xE052: [114],      # insert / help
    0xE053: [117],      # delete
    0xE05B: [55],       # left cmd
    0xE05C: [54],       # right cmd
    0xE05D: [110],      # menu
}

MAC_TO_SCAN = {}
for _scan, _codes in SCAN_TO_MAC.items():
    for _code in _codes:
        MAC_TO_SCAN.setdefault(_code, _scan)

# Noms de touches (disposition US, convention de la lib `keyboard`) -> scan code.
# Sert de repli quand la disposition .yml ne connaît pas la touche.
NAME_TO_SCAN = {
    "esc": 1, "escape": 1,
    "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
    "-": 12, "=": 13, "backspace": 14, "tab": 15,
    "q": 16, "w": 17, "e": 18, "r": 19, "t": 20, "y": 21, "u": 22, "i": 23, "o": 24, "p": 25,
    "[": 26, "]": 27, "enter": 28, "return": 28, "ctrl": 29, "left ctrl": 29,
    "a": 30, "s": 31, "d": 32, "f": 33, "g": 34, "h": 35, "j": 36, "k": 37, "l": 38,
    ";": 39, "'": 40, "`": 41, "²": 41, "shift": 42, "left shift": 42, "\\": 43,
    "z": 44, "x": 45, "c": 46, "v": 47, "b": 48, "n": 49, "m": 50,
    ",": 51, ".": 52, "/": 53, "right shift": 54, "num *": 55,
    "alt": 56, "left alt": 56, "option": 56, "space": 57, "caps lock": 58,
    "f1": 59, "f2": 60, "f3": 61, "f4": 62, "f5": 63, "f6": 64, "f7": 65, "f8": 66, "f9": 67, "f10": 68,
    "f11": 87, "f12": 88,
    "f13": 100, "f14": 101, "f15": 102, "f16": 103, "f17": 104, "f18": 105, "f19": 106, "f20": 107,
    "num lock": 69, "clear": 69,
    "num 7": 71, "num 8": 72, "num 9": 73, "num -": 74, "num 4": 75, "num 5": 76, "num 6": 77,
    "num +": 78, "num 1": 79, "num 2": 80, "num 3": 81, "num 0": 82, "num .": 83,
    "num enter": 0xE01C, "right ctrl": 0xE01D, "num /": 0xE035, "right alt": 0xE038, "alt gr": 0xE038,
    "home": 0xE047, "up": 0xE048, "page up": 0xE049, "left": 0xE04B, "right": 0xE04D,
    "end": 0xE04F, "down": 0xE050, "page down": 0xE051, "insert": 0xE052, "help": 0xE052,
    "delete": 0xE053, "cmd": 0xE05B, "left cmd": 0xE05B, "command": 0xE05B, "right cmd": 0xE05C,
    "windows": 0xE05B, "menu": 0xE05D,
}

# keycode macOS -> nom affiché (convention `keyboard`, disposition US)
MAC_KEY_NAMES = {}
for _name, _scan in NAME_TO_SCAN.items():
    for _code in SCAN_TO_MAC.get(_scan, []):
        MAC_KEY_NAMES.setdefault(_code, _name)
# Noms canoniques pour les modificateurs
MAC_KEY_NAMES.update({
    56: "shift", 60: "shift", 59: "ctrl", 62: "ctrl", 58: "alt", 61: "alt",
    55: "cmd", 54: "cmd", 57: "caps lock", 63: "fn", 53: "esc", 36: "enter", 76: "num enter",
    10: "²", 50: "²",
})

# keycode macOS d'un modificateur -> nom logique utilisé dans les raccourcis
MAC_MODIFIER_KEYCODES = {
    56: "shift", 60: "shift",
    59: "ctrl", 62: "ctrl",
    58: "alt", 61: "alt",
    55: "cmd", 54: "cmd",
}


def mac_keycodes_for_scan(scan):
    return SCAN_TO_MAC.get(scan, [])


def scan_for_mac_keycode(keycode):
    return MAC_TO_SCAN.get(keycode)


def name_for_mac_keycode(keycode):
    return MAC_KEY_NAMES.get(keycode)
