"""Backend Windows de DOSOFT.

Ce module regroupe, sans changement de comportement, le code win32 /
keyboard / WinRT qui se trouvait auparavant dans main.py, gui.py, logic.py
et radial_menu.py.
"""
import os
import sys
import time
import ctypes
import asyncio
import threading

import keyboard
import win32api
import win32con
import win32gui
import win32process

__all__ = [
    "PLATFORM_NAME", "MEDIA_KEY_PREFIX", "MODIFIERS", "MOUSE_BUTTONS", "KEY_DOWN", "KEY_UP", "UI_FONT",
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

PLATFORM_NAME = "windows"
MEDIA_KEY_PREFIX = "media:"  # jamais émis sous Windows
MODIFIERS = ("ctrl", "alt", "shift")
MOUSE_BUTTONS = ("left_click", "right_click", "middle_click", "mouse4", "mouse5")
KEY_DOWN = keyboard.KEY_DOWN
KEY_UP = keyboard.KEY_UP
UI_FONT = "Segoe UI"
TRANSPARENT_COLOR = "magenta"
NOTIF_ENGINES = ["v1", "v2", "v3"]

_MOD_VK = {"ctrl": win32con.VK_CONTROL, "alt": win32con.VK_MENU, "shift": win32con.VK_SHIFT}
_MOUSE_VK = {"left_click": 0x01, "right_click": 0x02, "middle_click": 0x04, "mouse4": 0x05, "mouse5": 0x06}


# ---------------------------------------------------------------------------
# Clavier / souris
# ---------------------------------------------------------------------------
def hook(callback, suppress=False):
    return keyboard.hook(callback, suppress=suppress)


def unhook(handle):
    keyboard.unhook(handle)


def unhook_all():
    keyboard.unhook_all()


def is_pressed(key):
    return keyboard.is_pressed(key)


def name_to_scan(token):
    try:
        return keyboard.key_to_scan_codes(token)[0]
    except Exception:
        return None


def is_modifier_pressed(name):
    vk = _MOD_VK.get(name)
    return vk is not None and win32api.GetAsyncKeyState(vk) < 0


def get_pressed_modifiers():
    return [m for m in MODIFIERS if is_modifier_pressed(m)]


def is_mouse_pressed(name):
    vk = _MOUSE_VK.get(name)
    return vk is not None and win32api.GetAsyncKeyState(vk) < 0


def get_cursor_pos():
    return win32api.GetCursorPos()


def release_modifiers():
    """Force Windows à relâcher les touches Ctrl, Alt et Shift."""
    try:
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
    except Exception:
        pass


def restore_modifiers(mods):
    try:
        if 'alt' in mods: win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        if 'ctrl' in mods: win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        if 'shift' in mods: win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Fenêtres de jeu
# ---------------------------------------------------------------------------
def list_game_windows(game_version):
    """Retourne [(hwnd, titre)] des fenêtres Dofus visibles."""
    windows_trouvees = []

    def enum_windows_callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            titre = win32gui.GetWindowText(hwnd)
            if not titre.strip(): return True
            if game_version == "Unity":
                if win32gui.GetClassName(hwnd) == "UnityWndClass":
                    windows_trouvees.append((hwnd, titre))
            elif game_version == "Rétro":
                if "Dofus Retro" in titre:
                    windows_trouvees.append((hwnd, titre))
        return True

    win32gui.EnumWindows(enum_windows_callback, None)
    return windows_trouvees


def get_foreground_window():
    return win32gui.GetForegroundWindow()


def focus_window(hwnd):
    if not hwnd: return
    try:
        if win32gui.IsIconic(hwnd): win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        tid, pid = win32process.GetWindowThreadProcessId(hwnd)
        ctypes.windll.user32.AllowSetForegroundWindow(pid)
        ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass


def terminate_window_process(hwnd):
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
        ctypes.windll.kernel32.TerminateProcess(handle, 0)
        ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        pass


def sort_windows(hwnds, leader_hwnd=None):
    """Range la barre des tâches Windows dans l'ordre de l'initiative."""
    if not hwnds: return
    try:
        for hwnd in hwnds:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
        time.sleep(0.3)
        for hwnd in hwnds:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            time.sleep(0.1)
        if leader_hwnd:
            focus_window(leader_hwnd)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Processus / système
# ---------------------------------------------------------------------------
def is_process_running(image_name):
    output = os.popen(f'tasklist /FI "IMAGENAME eq {image_name}" /NH').read().lower()
    return image_name.lower() in output


def kill_process_by_name(image_name):
    os.system(f"taskkill /F /IM {image_name} /T")


def prepare_process():
    # --- FORCAGE DU DPI AWARENESS (Règle les soucis 4K / Zoom Windows) ---
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def _run_as_admin():
    if getattr(sys, 'frozen', False):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
    else:
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)


def ensure_privileges():
    """Relance DOSOFT en administrateur si nécessaire (requis par keyboard)."""
    if not _is_admin():
        _run_as_admin()
        sys.exit()


def acquire_single_instance(i18n, app_title):
    import tkinter as tk
    from tkinter import messagebox
    mutex_name = "DOSOFT_SINGLE_INSTANCE_MUTEX"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        rep = messagebox.askyesno(
            i18n.t("header_instace_off", "Instance détectée"),
            i18n.t("popup_conflict_instance_text", "Une instance de DOSOFT est déjà en cours d'exécution !\n\nVoulez-vous fermer l'ancienne instance pour ouvrir celle-ci ?"))
        if rep:
            hwnd = win32gui.FindWindow(None, app_title)
            if hwnd:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
                    ctypes.windll.kernel32.TerminateProcess(handle, 0)
                    ctypes.windll.kernel32.CloseHandle(handle)
                except Exception:
                    pass
            time.sleep(0.5)
            root.destroy()
        else:
            root.destroy()
            sys.exit(0)
    return mutex


def load_system_keyboard_layout(layout_name):
    layout_map = {
        "azerty_fr": "0000040C",
        "qwerty_us": "00000409",
    }
    layout_code = layout_map.get(layout_name)
    if not layout_code:
        return
    try:
        ctypes.windll.user32.LoadKeyboardLayoutW(layout_code, 1 | 0x00000100)
    except Exception:
        pass


def default_settings_path():
    return "settings.json"


def show_error_box(title, text):
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)


def force_quit_self():
    my_pid = os.getpid()
    os.system(f"taskkill /F /PID {my_pid} /T")


# Les permissions macOS n'existent pas sous Windows.
def permissions_supported():
    return False


def check_permissions():
    return {}


def open_permission_settings(kind=None):
    pass


# ---------------------------------------------------------------------------
# Interface : barre système, transparence, icône
# ---------------------------------------------------------------------------
def create_tray(root, title, icon_path, menu_items):
    """menu_items : liste de (libellé, fonction_sans_argument, est_defaut)."""
    import pystray
    from pystray import MenuItem as item
    from PIL import Image
    try:
        image = Image.open(icon_path)
    except Exception:
        image = Image.new('RGB', (64, 64), color=(44, 62, 80))

    def wrap(func):
        return lambda icon, it: func()

    menu = pystray.Menu(*[item(label, wrap(func), default=default) for label, func, default in menu_items])
    tray_icon = pystray.Icon("dosoft_tray", image, title, menu)
    tray_icon.run_detached()
    return tray_icon


def setup_transparent_window(toplevel):
    toplevel.attributes("-transparentcolor", TRANSPARENT_COLOR)


def raise_overlay(toplevel):
    pass


def set_window_icon(root, icon_path="logo.ico"):
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass


def bring_app_to_front():
    pass


def install_app_handlers(root, on_reopen=None, on_quit=None):
    pass


# ---------------------------------------------------------------------------
# Notifications (Auto-Focus Rétro) via WinRT
# ---------------------------------------------------------------------------
def start_notification_listener(mode, handle_texts):
    """Démarre l'écoute des notifications toast Windows.

    handle_texts(list[str]) -> bool : retourne True si la notification a été
    reconnue comme une notification Dofus Rétro (elle est alors supprimée
    par le moteur v2).
    """
    try:
        from winrt.windows.ui.notifications.management import UserNotificationListener
        from winrt.windows.ui.notifications import NotificationKinds
    except ImportError:
        return

    def texts_of(n):
        binding = n.notification.visual.bindings[0]
        return [t.text for t in binding.get_text_elements()]

    async def engine_v1():
        while True:
            try:
                listener = UserNotificationListener.current
                access = await listener.request_access_async()
                if access != 1:
                    await asyncio.sleep(5)
                    continue
                seen_ids = set()
                first_pass = True
                while True:
                    try:
                        notifs = await listener.get_notifications_async(NotificationKinds.TOAST)
                        current_ids = set()
                        for n in notifs:
                            current_ids.add(n.id)
                            if n.id not in seen_ids:
                                seen_ids.add(n.id)
                                if not first_pass:
                                    try: handle_texts(texts_of(n))
                                    except Exception: pass
                        seen_ids.intersection_update(current_ids)
                        first_pass = False
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)
            except Exception:
                pass
            await asyncio.sleep(3)

    # MOTEUR V2 : AVEC NETTOYAGE NOTIFICATIONS
    async def engine_v2():
        while True:
            try:
                listener = UserNotificationListener.current
                access = await listener.request_access_async()
                if access != 1:
                    await asyncio.sleep(5)
                    continue
                seen_ids = set()
                first_pass = True

                async def remove_notif_delayed(notif_id):
                    await asyncio.sleep(1.0)
                    try: listener.remove_notification(notif_id)
                    except Exception: pass

                while True:
                    try:
                        notifs = await listener.get_notifications_async(NotificationKinds.TOAST)
                        current_ids = set()
                        for n in notifs:
                            current_ids.add(n.id)
                            if n.id not in seen_ids:
                                seen_ids.add(n.id)
                                if not first_pass:
                                    try:
                                        if handle_texts(texts_of(n)):
                                            asyncio.create_task(remove_notif_delayed(n.id))
                                    except Exception:
                                        pass
                        seen_ids.intersection_update(current_ids)
                        first_pass = False
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)
            except Exception:
                pass
            await asyncio.sleep(3)

    # MOTEUR V3 : POLLING RAPIDE SANS NETTOYAGE
    async def engine_v3():
        while True:
            try:
                listener = UserNotificationListener.current
                access = await listener.request_access_async()
                if access != 1:
                    await asyncio.sleep(5)
                    continue
                seen_ids = set()
                first_pass = True
                while True:
                    try:
                        notifs = await listener.get_notifications_async(NotificationKinds.TOAST)
                        current_ids = {n.id for n in notifs}
                        for n in notifs:
                            if n.id not in seen_ids:
                                seen_ids.add(n.id)
                                if not first_pass:
                                    try: handle_texts(texts_of(n))
                                    except Exception: pass
                        seen_ids.intersection_update(current_ids)
                    except Exception:
                        pass
                    first_pass = False
                    await asyncio.sleep(0.3)
            except Exception:
                pass
            await asyncio.sleep(3)

    engine = {"v1": engine_v1, "v3": engine_v3}.get(mode, engine_v2)

    def run_async_loop():
        try:
            import pythoncom
            pythoncom.CoInitializeEx(0, pythoncom.COINIT_MULTITHREADED)
        except Exception:
            pass
        while True:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(engine())
            except Exception:
                pass
            finally:
                try: loop.close()
                except Exception: pass
            time.sleep(3)

    threading.Thread(target=run_async_loop, daemon=True).start()
