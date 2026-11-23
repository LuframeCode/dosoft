"""Backend macOS de DOSOFT.

Technologies utilisées :
- Quartz Event Tap        : raccourcis clavier/souris globaux (équivalent `keyboard`)
- Accessibility (AX)      : liste des fenêtres Dofus, titres, mise au premier plan
- CoreGraphics WindowList : fenêtre active
- AppKit NSStatusItem     : icône dans la barre des menus (équivalent pystray)
- AX sur le Centre de notifications : Auto-Focus Rétro (équivalent WinRT)

Permission requise : Réglages Système > Confidentialité et sécurité >
Accessibilité (DOSOFT doit y être coché).
"""
import os
import sys
import time
import fcntl
import queue
import shutil
import signal
import threading
import subprocess

import objc
import Quartz
import ApplicationServices as AX
from AppKit import (
    NSApplication, NSWorkspace, NSRunningApplication, NSStatusBar, NSMenu, NSMenuItem,
    NSImage, NSVariableStatusItemLength, NSApplicationActivationPolicyRegular,
)
from Foundation import NSObject, NSBundle, NSURL

from . import mac_keycodes as kc
from . import mac_notifications

__all__ = [
    "PLATFORM_NAME", "MODIFIERS", "MOUSE_BUTTONS", "KEY_DOWN", "KEY_UP", "UI_FONT",
    "TRANSPARENT_COLOR", "NOTIF_ENGINES",
    "hook", "unhook", "unhook_all", "is_pressed", "name_to_scan",
    "get_pressed_modifiers", "is_modifier_pressed", "is_mouse_pressed",
    "get_cursor_pos", "release_modifiers", "restore_modifiers",
    "list_game_windows", "get_foreground_window", "focus_window",
    "terminate_window_process", "sort_windows",
    "is_process_running", "kill_process_by_name",
    "prepare_process", "ensure_privileges", "acquire_single_instance",
    "load_system_keyboard_layout", "default_settings_path", "show_error_box",
    "force_quit_self", "create_tray", "start_notification_listener",
    "setup_transparent_window", "raise_overlay", "set_window_icon", "bring_app_to_front",
    "install_app_handlers", "check_permissions", "open_permission_settings",
    "permissions_supported",
]

PLATFORM_NAME = "macos"
MODIFIERS = ("ctrl", "alt", "shift", "cmd")
MOUSE_BUTTONS = ("left_click", "right_click", "middle_click", "mouse4", "mouse5")
KEY_DOWN = "down"
KEY_UP = "up"
UI_FONT = "Helvetica Neue"
TRANSPARENT_COLOR = "systemTransparent"
NOTIF_ENGINES = ["v1", "v2", "v3"]

APP_SUPPORT_DIR = os.path.expanduser("~/Library/Application Support/Dosoft")

_MOD_FLAGS = {
    "shift": Quartz.kCGEventFlagMaskShift,
    "ctrl": Quartz.kCGEventFlagMaskControl,
    "alt": Quartz.kCGEventFlagMaskAlternate,
    "cmd": Quartz.kCGEventFlagMaskCommand,
}
_MOUSE_BUTTON_NUM = {"left_click": 0, "right_click": 1, "middle_click": 2, "mouse4": 3, "mouse5": 4}
_HID_STATE = Quartz.kCGEventSourceStateHIDSystemState


# ===========================================================================
# Clavier / souris globaux : Quartz Event Tap
# ===========================================================================
class KeyEvent:
    """Événement compatible avec ceux de la lib `keyboard` (event_type, scan_code, name)."""
    __slots__ = ("event_type", "scan_code", "name", "keycode")

    def __init__(self, event_type, scan_code, name, keycode):
        self.event_type = event_type
        self.scan_code = scan_code
        self.name = name
        self.keycode = keycode

    def __repr__(self):
        return f"KeyEvent({self.event_type}, scan={self.scan_code}, name={self.name!r}, kc={self.keycode})"


class _InputMonitor:
    def __init__(self):
        self._hooks = {}
        self._next_id = 1
        self._lock = threading.Lock()
        self._down_keys = set()
        self._down_buttons = set()
        self._flags = 0
        self._tap = None
        self._started = False
        self.active = False       # tap actif (peut bloquer des touches)
        self.listen_only = False  # tap en écoute seule (aucun blocage possible)
        self._callback_ref = self._callback

    # ---- cycle de vie -----------------------------------------------------
    def ensure_started(self):
        if self._started:
            return
        self._started = True
        threading.Thread(target=self._run, name="dosoft-eventtap", daemon=True).start()

    def _create_tap(self):
        mask = 0
        for t in (Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp, Quartz.kCGEventFlagsChanged,
                  Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp,
                  Quartz.kCGEventRightMouseDown, Quartz.kCGEventRightMouseUp,
                  Quartz.kCGEventOtherMouseDown, Quartz.kCGEventOtherMouseUp):
            mask |= Quartz.CGEventMaskBit(t)
        tap = Quartz.CGEventTapCreate(Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
                                      Quartz.kCGEventTapOptionDefault, mask, self._callback_ref, None)
        if tap:
            return tap, False
        tap = Quartz.CGEventTapCreate(Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
                                      Quartz.kCGEventTapOptionListenOnly, mask, self._callback_ref, None)
        if tap:
            return tap, True
        return None, False

    def _run(self):
        # On réessaie tant que la permission Accessibilité n'est pas accordée :
        # les raccourcis se mettent à fonctionner dès qu'elle l'est, sans redémarrage.
        while True:
            tap, listen_only = self._create_tap()
            if tap:
                break
            time.sleep(2.0)
        self._tap = tap
        self.listen_only = listen_only
        self.active = True
        source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(tap, True)
        Quartz.CFRunLoopRun()

    # ---- callback du tap ---------------------------------------------------
    def _callback(self, proxy, event_type, event, refcon):
        try:
            if event_type in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
                self._down_keys.clear()
                self._down_buttons.clear()
                if self._tap is not None:
                    Quartz.CGEventTapEnable(self._tap, True)
                return event

            if event_type in (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventRightMouseDown, Quartz.kCGEventOtherMouseDown):
                self._down_buttons.add(Quartz.CGEventGetIntegerValueField(event, Quartz.kCGMouseEventButtonNumber))
                return event
            if event_type in (Quartz.kCGEventLeftMouseUp, Quartz.kCGEventRightMouseUp, Quartz.kCGEventOtherMouseUp):
                self._down_buttons.discard(Quartz.CGEventGetIntegerValueField(event, Quartz.kCGMouseEventButtonNumber))
                return event

            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            flags = Quartz.CGEventGetFlags(event)
            self._flags = flags

            if event_type == Quartz.kCGEventFlagsChanged:
                mod = kc.MAC_MODIFIER_KEYCODES.get(keycode)
                if mod is None:
                    return event
                is_down = bool(flags & _MOD_FLAGS[mod]) and keycode not in self._down_keys
                if is_down:
                    self._down_keys.add(keycode)
                else:
                    self._down_keys.discard(keycode)
                ev_type = KEY_DOWN if is_down else KEY_UP
            elif event_type == Quartz.kCGEventKeyDown:
                self._down_keys.add(keycode)
                ev_type = KEY_DOWN
            elif event_type == Quartz.kCGEventKeyUp:
                self._down_keys.discard(keycode)
                ev_type = KEY_UP
            else:
                return event

            scan = kc.scan_for_mac_keycode(keycode)
            if scan is None:
                scan = 0x10000 + keycode  # touche inconnue : scan code unique hors plage PC
            ev = KeyEvent(ev_type, scan, kc.name_for_mac_keycode(keycode) or f"key{keycode}", keycode)

            suppress = False
            with self._lock:
                hooks = list(self._hooks.values())
            for cb, sup in hooks:
                try:
                    cb(ev)
                except Exception:
                    pass
                suppress = suppress or sup
            if suppress and not self.listen_only:
                return None
        except Exception:
            pass
        return event

    # ---- API ---------------------------------------------------------------
    def add_hook(self, callback, suppress=False):
        self.ensure_started()
        with self._lock:
            hid = self._next_id
            self._next_id += 1
            self._hooks[hid] = (callback, suppress)
        return hid

    def remove_hook(self, hid):
        with self._lock:
            self._hooks.pop(hid, None)

    def remove_all(self):
        with self._lock:
            self._hooks.clear()

    def keycode_down(self, keycode):
        if keycode in self._down_keys:
            return True
        try:
            return bool(Quartz.CGEventSourceKeyState(_HID_STATE, keycode))
        except Exception:
            return False

    def button_down(self, button):
        if button in self._down_buttons:
            return True
        try:
            return bool(Quartz.CGEventSourceButtonState(_HID_STATE, button))
        except Exception:
            return False

    def modifier_down(self, name):
        mask = _MOD_FLAGS.get(name)
        if mask is None:
            return False
        try:
            if Quartz.CGEventSourceFlagsState(_HID_STATE) & mask:
                return True
        except Exception:
            pass
        codes = [c for c, m in kc.MAC_MODIFIER_KEYCODES.items() if m == name]
        return any(c in self._down_keys for c in codes)


_input = _InputMonitor()


def hook(callback, suppress=False):
    return _input.add_hook(callback, suppress)


def unhook(handle):
    _input.remove_hook(handle)


def unhook_all():
    _input.remove_all()


def name_to_scan(token):
    if not token:
        return None
    return kc.NAME_TO_SCAN.get(str(token).lower().strip())


def is_pressed(key):
    """Équivalent de keyboard.is_pressed : accepte un scan code (int) ou un nom."""
    if isinstance(key, str):
        name = key.lower().strip()
        if name in _MOD_FLAGS:
            return is_modifier_pressed(name)
        scan = name_to_scan(name)
    else:
        scan = key
    if scan is None:
        return False
    if scan >= 0x10000:
        return _input.keycode_down(scan - 0x10000)
    return any(_input.keycode_down(code) for code in kc.mac_keycodes_for_scan(scan))


def is_modifier_pressed(name):
    return _input.modifier_down(name)


def get_pressed_modifiers():
    return [m for m in MODIFIERS if is_modifier_pressed(m)]


def is_mouse_pressed(name):
    button = _MOUSE_BUTTON_NUM.get(name)
    return button is not None and _input.button_down(button)


def get_cursor_pos():
    loc = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
    return int(loc.x), int(loc.y)


def release_modifiers():
    # Sous macOS la mise au premier plan via Accessibilité n'est pas bloquée par
    # les modificateurs enfoncés : inutile (et risqué) de simuler des relâchements.
    pass


def restore_modifiers(mods):
    pass


# ===========================================================================
# Accessibilité (AX) : fenêtres
# ===========================================================================
_AXGetWindow = None


def _load_private_ax():
    global _AXGetWindow
    for bundle_id in ("com.apple.HIServices", "com.apple.ApplicationServices"):
        bundle = NSBundle.bundleWithIdentifier_(bundle_id)
        if bundle is None:
            continue
        funcs = {}
        try:
            objc.loadBundleFunctions(bundle, funcs, [("_AXUIElementGetWindow", b"i@o^I")])
        except Exception:
            continue
        if "_AXUIElementGetWindow" in funcs:
            _AXGetWindow = funcs["_AXUIElementGetWindow"]
            return


_load_private_ax()


def _ax_attr(element, attr):
    try:
        err, value = AX.AXUIElementCopyAttributeValue(element, attr, None)
        if err == 0:
            return value
    except Exception:
        pass
    return None


def _ax_set(element, attr, value):
    try:
        return AX.AXUIElementSetAttributeValue(element, attr, value) == 0
    except Exception:
        return False


def _ax_window_id(element):
    if _AXGetWindow is None:
        return None
    try:
        err, wid = _AXGetWindow(element, None)
        if err == 0 and wid:
            return int(wid)
    except Exception:
        pass
    return None


def _cg_windows(on_screen_only=True):
    opts = Quartz.kCGWindowListExcludeDesktopElements
    opts |= Quartz.kCGWindowListOptionOnScreenOnly if on_screen_only else Quartz.kCGWindowListOptionAll
    return Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID) or []


def _is_dofus_app(app, game_version):
    try:
        if app.activationPolicy() != NSApplicationActivationPolicyRegular:
            return False
        bid = (app.bundleIdentifier() or "").lower()
        name = (app.localizedName() or "").lower()
        exe = ""
        url = app.executableURL()
        if url is not None:
            exe = (url.lastPathComponent() or "").lower()
    except Exception:
        return False
    if "launcher" in bid or "launcher" in name:
        return False
    if bid.startswith("com.apple."):
        return False  # ex : « AutoFill (Dofus) »
    is_dofus = "dofus" in bid or name.startswith("dofus") or exe.startswith("dofus")
    if not is_dofus:
        return False
    is_retro = "retro" in bid or "retro" in name or "retro" in exe
    if game_version == "Rétro":
        return is_retro
    return not is_retro


class _WindowRegistry:
    """Cache handle (CGWindowID) -> infos de fenêtre (pid, élément AX, titre)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.windows = {}
        self._fg_cache = (0.0, None)

    def scan(self, game_version):
        result = []
        found = {}
        cg_all = None
        for app in NSWorkspace.sharedWorkspace().runningApplications():
            if not _is_dofus_app(app, game_version):
                continue
            pid = app.processIdentifier()
            ax_app = AX.AXUIElementCreateApplication(pid)
            ax_windows = _ax_attr(ax_app, AX.kAXWindowsAttribute) or []
            entries = []
            for idx, win in enumerate(ax_windows):
                subrole = _ax_attr(win, AX.kAXSubroleAttribute)
                if subrole and subrole not in ("AXStandardWindow", "AXDialog"):
                    continue
                title = _ax_attr(win, AX.kAXTitleAttribute) or ""
                wid = _ax_window_id(win)
                entries.append([wid, str(title), win])

            if not entries:
                # Repli CoreGraphics (fenêtre sur un autre Bureau, AX indisponible…)
                if cg_all is None:
                    cg_all = _cg_windows(on_screen_only=False)
                candidates = []
                for w in cg_all:
                    if w.get("kCGWindowOwnerPID") == pid and w.get("kCGWindowLayer") == 0:
                        b = w.get("kCGWindowBounds") or {}
                        if b.get("Width", 0) < 100 or b.get("Height", 0) < 100:
                            continue
                        candidates.append(w)
                # Unity crée des fenêtres annexes hors écran : on garde les fenêtres
                # visibles, sinon (autre Bureau, minimisée) la plus grande.
                visible = [w for w in candidates if w.get("kCGWindowIsOnscreen")]
                if not visible and candidates:
                    visible = [max(candidates, key=lambda w: w["kCGWindowBounds"]["Width"] * w["kCGWindowBounds"]["Height"])]
                for w in visible:
                    title = w.get("kCGWindowName") or app.localizedName() or "Dofus"
                    entries.append([int(w.get("kCGWindowNumber")), str(title), None])

            for entry in entries:
                if entry[0] is None:
                    # _AXUIElementGetWindow indisponible : identifiant synthétique stable
                    entry[0] = -(pid * 100 + len(found) % 100)
                wid, title, ax_win = entry
                found[wid] = {"pid": pid, "ax": ax_win, "title": title}

                if not title.strip():
                    continue
                if game_version == "Rétro" and "Dofus Retro" not in title:
                    continue
                result.append((wid, title))

        with self.lock:
            self.windows = found
        return result

    def info(self, handle):
        with self.lock:
            return self.windows.get(handle)

    def pid_for(self, handle):
        info = self.info(handle)
        if info:
            return info["pid"]
        for w in _cg_windows(on_screen_only=False):
            if w.get("kCGWindowNumber") == handle:
                return w.get("kCGWindowOwnerPID")
        return None

    def ax_for(self, handle, pid):
        info = self.info(handle)
        if info and info.get("ax") is not None:
            return info["ax"]
        ax_app = AX.AXUIElementCreateApplication(pid)
        wins = _ax_attr(ax_app, AX.kAXWindowsAttribute) or []
        for win in wins:
            if _ax_window_id(win) == handle:
                return win
        return wins[0] if len(wins) == 1 else None

    def foreground(self):
        now = time.monotonic()
        ts, cached = self._fg_cache
        if now - ts < 0.05:
            return cached
        fg = None
        try:
            for w in _cg_windows(on_screen_only=True):
                if w.get("kCGWindowLayer") == 0 and w.get("kCGWindowOwnerPID") != os.getpid():
                    b = w.get("kCGWindowBounds") or {}
                    if b.get("Width", 0) < 50 or b.get("Height", 0) < 50:
                        continue
                    fg = int(w.get("kCGWindowNumber"))
                    pid = w.get("kCGWindowOwnerPID")
                    # Identifiants synthétiques : on retrouve la fenêtre par son pid
                    with self.lock:
                        if fg not in self.windows:
                            for h, info in self.windows.items():
                                if h < 0 and info["pid"] == pid:
                                    fg = h
                                    break
                    break
        except Exception:
            pass
        self._fg_cache = (now, fg)
        return fg


_registry = _WindowRegistry()


def list_game_windows(game_version):
    return _registry.scan(game_version)


def get_foreground_window():
    return _registry.foreground()


def _activate_pid(pid):
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app is not None:
        try:
            if app.isHidden():
                app.unhide()
        except Exception:
            pass
        try:
            app.activateWithOptions_(1 << 1)  # NSApplicationActivateIgnoringOtherApps
        except Exception:
            pass
    return app


def focus_window(handle):
    if not handle:
        return
    try:
        pid = _registry.pid_for(handle)
        if not pid:
            return
        ax_win = _registry.ax_for(handle, pid)
        if ax_win is not None and _ax_attr(ax_win, AX.kAXMinimizedAttribute):
            _ax_set(ax_win, AX.kAXMinimizedAttribute, False)
        ax_app = AX.AXUIElementCreateApplication(pid)
        _ax_set(ax_app, AX.kAXFrontmostAttribute, True)
        if ax_win is not None:
            _ax_set(ax_win, AX.kAXMainAttribute, True)
            _ax_set(ax_win, AX.kAXFocusedAttribute, True)
            try:
                AX.AXUIElementPerformAction(ax_win, AX.kAXRaiseAction)
            except Exception:
                pass
        _activate_pid(pid)
        _registry._fg_cache = (0.0, None)
    except Exception:
        pass


def terminate_window_process(handle):
    pid = _registry.pid_for(handle)
    if not pid:
        return
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    try:
        if app is not None and app.forceTerminate():
            return
    except Exception:
        pass
    try:
        os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def sort_windows(handles, leader_handle=None):
    """Équivalent macOS de « Trier Barre Windows ».

    Le Dock ne peut pas être réordonné : on active les fenêtres de la dernière
    à la première pour que la pile des fenêtres et le sélecteur Cmd+Tab suivent
    l'ordre de l'initiative, puis on redonne le focus au chef.
    """
    if not handles:
        return
    try:
        for handle in reversed(handles):
            focus_window(handle)
            time.sleep(0.12)
        if leader_handle:
            focus_window(leader_handle)
    except Exception:
        pass


# ===========================================================================
# Processus / système
# ===========================================================================
def is_process_running(image_name):
    name = os.path.splitext(image_name)[0]
    try:
        out = subprocess.run(["pgrep", "-ix", name], capture_output=True, timeout=3)
        return out.returncode == 0
    except Exception:
        return False


def kill_process_by_name(image_name):
    name = os.path.splitext(image_name)[0]
    try:
        subprocess.run(["pkill", "-9", "-ix", name], capture_output=True, timeout=3)
    except Exception:
        pass


def resource_dir():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def prepare_process():
    # Les chemins relatifs (skin/, sounds/, logo.ico…) sont résolus depuis le
    # dossier des ressources, y compris dans le bundle .app.
    try:
        os.chdir(resource_dir())
    except Exception:
        pass
    os.makedirs(APP_SUPPORT_DIR, exist_ok=True)


def permissions_supported():
    return True


def check_permissions():
    try:
        accessibility = bool(AX.AXIsProcessTrusted())
    except Exception:
        accessibility = False
    return {"accessibility": accessibility}


def ensure_privileges():
    """Pas d'élévation admin sur macOS : on demande la permission Accessibilité.

    La fenêtre système d'autorisation est affichée une seule fois par macOS ;
    l'application continue de fonctionner et active les raccourcis dès que la
    permission est accordée.
    """
    try:
        if not AX.AXIsProcessTrusted():
            AX.AXIsProcessTrustedWithOptions({AX.kAXTrustedCheckOptionPrompt: True})
    except Exception:
        pass
    _input.ensure_started()


def open_permission_settings(kind="accessibility"):
    anchors = {
        "accessibility": "Privacy_Accessibility",
        "input_monitoring": "Privacy_ListenEvent",
    }
    url = "x-apple.systempreferences:com.apple.preference.security?" + anchors.get(kind, "Privacy_Accessibility")
    try:
        subprocess.Popen(["open", url])
    except Exception:
        pass


_lock_file = None


def acquire_single_instance(i18n, app_title):
    """Instance unique via un verrou fcntl dans Application Support."""
    global _lock_file
    os.makedirs(APP_SUPPORT_DIR, exist_ok=True)
    path = os.path.join(APP_SUPPORT_DIR, "dosoft.lock")
    _lock_file = open(path, "a+")
    try:
        fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        rep = messagebox.askyesno(
            i18n.t("header_instace_off", "Instance détectée"),
            i18n.t("popup_conflict_instance_text", "Une instance de DOSOFT est déjà en cours d'exécution !\n\nVoulez-vous fermer l'ancienne instance pour ouvrir celle-ci ?"))
        root.destroy()
        if not rep:
            sys.exit(0)
        try:
            _lock_file.seek(0)
            old_pid = int((_lock_file.read() or "0").strip() or 0)
        except Exception:
            old_pid = 0
        if old_pid and old_pid != os.getpid():
            try:
                os.kill(old_pid, signal.SIGKILL)
            except Exception:
                pass
        for _ in range(30):
            try:
                fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                time.sleep(0.1)
    _lock_file.seek(0)
    _lock_file.truncate()
    _lock_file.write(str(os.getpid()))
    _lock_file.flush()
    return _lock_file


def load_system_keyboard_layout(layout_name):
    # Les keycodes macOS sont positionnels : aucune disposition système à charger.
    pass


def default_settings_path():
    os.makedirs(APP_SUPPORT_DIR, exist_ok=True)
    path = os.path.join(APP_SUPPORT_DIR, "settings.json")
    if not os.path.exists(path):
        # Migration d'un settings.json local (lancement depuis les sources)
        legacy = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")
        if os.path.exists(legacy):
            try:
                shutil.copy(legacy, path)
            except Exception:
                pass
    return path


def show_error_box(title, text):
    import tkinter as tk
    from tkinter import messagebox
    root = tk._default_root
    temp = None
    if root is None:
        temp = tk.Tk()
        temp.withdraw()
        temp.attributes("-topmost", True)
    try:
        messagebox.showerror(title, text, parent=temp or root)
    finally:
        if temp is not None:
            temp.destroy()


def force_quit_self():
    os._exit(0)


# ===========================================================================
# Interface : barre des menus, overlay transparent, icône, Dock
# ===========================================================================
class DosoftStatusTarget(NSObject):
    def initWithCallbacks_(self, callbacks):
        self = objc.super(DosoftStatusTarget, self).init()
        if self is None:
            return None
        self.callbacks = callbacks
        return self

    def menuAction_(self, sender):
        try:
            self.callbacks[sender.tag()]()
        except Exception:
            pass


class _StatusItem:
    def __init__(self, root, title, icon_path, menu_items):
        # IMPORTANT : les actions de menu Cocoa s'exécutent pendant la boucle
        # d'événements de Tk, qui détient le verrou Tcl. Appeler Tk (root.after…)
        # directement depuis le callback provoque un interblocage : on passe donc
        # par une file, vidée par un timer Tk.
        self._queue = queue.SimpleQueue()
        self._root = root
        self._target = DosoftStatusTarget.alloc().initWithCallbacks_(
            [(lambda f=func: self._queue.put(f)) for _, func, _ in menu_items])
        self._poll()
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        button = self.item.button()
        image = _load_status_image(icon_path)
        if image is not None:
            button.setImage_(image)
        else:
            button.setTitle_("DO")
        button.setToolTip_(title)
        menu = NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)
        for idx, (label, _, _) in enumerate(menu_items):
            mi = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(label, "menuAction:", "")
            mi.setTarget_(self._target)
            mi.setTag_(idx)
            mi.setEnabled_(True)
            menu.addItem_(mi)
        self.item.setMenu_(menu)

    def _poll(self):
        try:
            while True:
                func = self._queue.get_nowait()
                try:
                    func()
                except Exception:
                    pass
        except queue.Empty:
            pass
        try:
            self._root.after(100, self._poll)
        except Exception:
            pass

    def stop(self):
        try:
            NSStatusBar.systemStatusBar().removeStatusItem_(self.item)
        except Exception:
            pass


def _load_status_image(icon_path):
    candidates = ["resources/mac/tray.png", icon_path]
    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            if path.lower().endswith(".ico"):
                from PIL import Image
                png = os.path.join(APP_SUPPORT_DIR, "tray.png")
                Image.open(path).convert("RGBA").resize((44, 44)).save(png)
                path = png
            img = NSImage.alloc().initWithContentsOfFile_(os.path.abspath(path))
            if img is not None:
                img.setSize_((18, 18))
                return img
        except Exception:
            continue
    return None


def create_tray(root, title, icon_path, menu_items):
    """Icône dans la barre des menus macOS. menu_items : [(libellé, fonction, défaut)]."""
    return _StatusItem(root, title, icon_path, menu_items)


def _ns_window_for(toplevel):
    marker = toplevel.wm_title()
    for w in NSApplication.sharedApplication().windows():
        try:
            if w.title() == marker:
                return w
        except Exception:
            continue
    return None


def setup_transparent_window(toplevel):
    """Fenêtre overlay transparente (roue radiale)."""
    toplevel.attributes("-transparent", True)
    toplevel.configure(bg=TRANSPARENT_COLOR)
    toplevel.wm_title(f"dosoft-overlay-{id(toplevel)}")


def raise_overlay(toplevel):
    """À appeler après chaque affichage de l'overlay (Tk réinitialise le niveau
    de la fenêtre au mappage) : au-dessus du jeu, sur tous les Bureaux, par-dessus
    une fenêtre en plein écran, et transparente aux clics."""
    try:
        toplevel.update_idletasks()
        nsw = getattr(toplevel, "_dosoft_nswindow", None) or _ns_window_for(toplevel)
        if nsw is None:
            return
        toplevel._dosoft_nswindow = nsw
        nsw.setLevel_(25)  # NSStatusWindowLevel
        nsw.setHidesOnDeactivate_(False)
        # CanJoinAllSpaces | IgnoresCycle | FullScreenAuxiliary
        nsw.setCollectionBehavior_((1 << 0) | (1 << 6) | (1 << 8))
        nsw.setIgnoresMouseEvents_(True)
        nsw.setHasShadow_(False)
        nsw.orderFrontRegardless()
    except Exception:
        pass


def set_window_icon(root, icon_path="logo.ico"):
    if getattr(sys, "frozen", False):
        return  # l'icône du bundle .app est utilisée
    try:
        from PIL import Image, ImageTk
        img = ImageTk.PhotoImage(Image.open(icon_path).convert("RGBA").resize((256, 256)))
        root.iconphoto(True, img)
        root._dosoft_icon = img
    except Exception:
        pass


def bring_app_to_front():
    try:
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    except Exception:
        pass


def install_app_handlers(root, on_reopen=None, on_quit=None):
    """Clic sur l'icône du Dock -> réafficher ; Cmd+Q -> quitter."""
    try:
        if on_reopen:
            root.createcommand("::tk::mac::ReopenApplication", on_reopen)
        if on_quit:
            root.createcommand("::tk::mac::Quit", on_quit)
    except Exception:
        pass


# ===========================================================================
# Notifications (Auto-Focus Rétro)
# ===========================================================================
def start_notification_listener(mode, handle_texts):
    mac_notifications.start(mode, handle_texts)
