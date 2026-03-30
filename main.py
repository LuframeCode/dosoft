import asyncio
import ctypes
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, Optional

import customtkinter as ctk
import keyboard
import pystray
import requests
import tkinter as tk
import win32api
import win32con
import win32gui
import win32process
from PIL import Image
from pystray import MenuItem as item
from tkinter import messagebox

from config_manager import Config
from gui import OrganizerGUI
from i18n import tr
from keymap import (
    MODIFIER_TOKENS,
    MOUSE_TOKENS,
    get_scan_code_for_key,
    normalize_key_name,
)
from logic import DofusLogic
from radial_menu import RadialMenu
from utils import resource_path


APP_NAME = "DOSOFT"
APP_VERSION = "1.2.2"
WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"
VERSION_URL = "https://raw.githubusercontent.com/LuframeCode/Dosoft/main/version.json"

DEFAULT_POLL_INTERVAL = 0.02
NOTIFICATION_POLL_INTERVAL = 0.5


def t_cfg(config, text, **kwargs):
    return tr(config, text, **kwargs)


def safe_print(message: str) -> None:
    try:
        print(message)
    except Exception:
        pass


def safe_config_save(config, force=False):
    if hasattr(config, "touch"):
        try:
            config.touch()
        except Exception:
            pass

    try:
        config.save(force=force)
    except TypeError:
        config.save()


def configure_dpi() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


configure_dpi()

try:
    from winrt.windows.ui.notifications.management import UserNotificationListener
    from winrt.windows.ui.notifications import NotificationKinds

    WINSDK_AVAILABLE = True
except Exception as exc:
    WINSDK_AVAILABLE = False
    UserNotificationListener = None
    NotificationKinds = None
    safe_print(f"[WARN] WinRT notifications disabled: {exc}")


@dataclass
class HotkeyRegistry:
    keyboard_actions: Dict[tuple[FrozenSet[str], int], Callable[[], None]] = field(default_factory=dict)
    mouse_actions: Dict[str, Callable[[], None]] = field(default_factory=dict)
    mouse_states: Dict[str, bool] = field(default_factory=dict)

    def clear(self) -> None:
        self.keyboard_actions.clear()
        self.mouse_actions.clear()
        self.mouse_states.clear()


class TrayService:
    def __init__(self, app: "OrganizerApp") -> None:
        self.app = app
        self.icon: Optional[pystray.Icon] = None

    def start(self) -> None:
        icon_path = resource_path("logo.ico")
        try:
            image = Image.open(icon_path)
        except Exception:
            return

        menu = pystray.Menu(
            item(self.app._t("Afficher/Cacher"), self._toggle, default=True),
            item(self.app._t("Trier Barre Windows"), self._sort_taskbar),
            item(self.app._t("Rafraîchir"), self._refresh),
            item(self.app._t("Quitter"), self._quit),
        )

        self.icon = pystray.Icon("dosoft_tray", image, APP_NAME, menu)
        self.icon.run_detached()

    def stop(self) -> None:
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass

    def _refresh(self, icon, menu_item) -> None:
        self.app.gui.root.after(0, self.app.refresh)

    def _sort_taskbar(self, icon, menu_item) -> None:
        self.app.gui.root.after(0, self.app.gui.trigger_sort_taskbar)

    def _toggle(self, icon, menu_item) -> None:
        self.app.gui.root.after(0, self.app.toggle_window_visibility)

    def _quit(self, icon, menu_item) -> None:
        self.app.gui.root.after(0, self.app.quit_app)


class HotkeyService:
    def __init__(self, app: "OrganizerApp") -> None:
        self.app = app
        self.registry = HotkeyRegistry()
        self._hook_active = False

    def reset(self) -> None:
        try:
            keyboard.unhook_all()
        except Exception:
            pass

        self.registry.clear()
        self._hook_active = False

    def rebuild(self) -> None:
        self.reset()
        self._register_builtin_actions()
        self._register_config_actions()
        self._register_global_hook()

    def _register_builtin_actions(self) -> None:
        self.register_action("f5", self.app.refresh)
        self.register_action("f12", self.app.quit_app)

    def _register_config_actions(self) -> None:
        cfg = self.app.config.data

        if cfg.get("prev_key"):
            self.register_action(cfg["prev_key"], self.app.prev_char)

        if cfg.get("next_key"):
            self.register_action(cfg["next_key"], self.app.next_char)

        if cfg.get("leader_key"):
            self.register_action(cfg["leader_key"], self.app.focus_leader)

        if cfg.get("toggle_app_key"):
            self.register_action(
                cfg["toggle_app_key"],
                lambda: self.app.gui.root.after(0, self.app.gui.toggle_visibility),
            )

        self._register_advanced_binds()

    def _register_advanced_binds(self) -> None:
        cfg = self.app.config.data
        mode = cfg.get("advanced_bind_mode", "cycle")

        if mode == "cycle":
            row_binds = cfg.get("cycle_row_binds", [])
            for index, bind_str in enumerate(row_binds):
                effective_bind = self.app.apply_advanced_modifier(bind_str)
                if effective_bind:
                    self.register_action(
                        effective_bind,
                        lambda idx=index: self.app.execute_advanced_and_update("cycle", idx),
                    )

        elif mode == "bind":
            char_binds = cfg.get("persistent_character_binds", {})
            for pseudo, bind_str in char_binds.items():
                effective_bind = self.app.apply_advanced_modifier(bind_str)
                if effective_bind:
                    self.register_action(
                        effective_bind,
                        lambda ps=pseudo: self.app.execute_advanced_and_update("bind", ps),
                    )

    def register_action(self, hotkey_str: str, func: Callable[[], None]) -> None:
        hotkey_str = normalize_key_name(hotkey_str) if isinstance(hotkey_str, str) else hotkey_str
        if not hotkey_str:
            return

        normalized_hotkey = str(hotkey_str).lower().strip()

        if "click" in normalized_hotkey or "mouse" in normalized_hotkey:
            self.registry.mouse_actions[normalized_hotkey] = func
            return

        parts = [normalize_key_name(part) for part in normalized_hotkey.split("+") if part]
        mods: set[str] = set()
        main_scan: Optional[int] = None

        for part in parts:
            if part in MODIFIER_TOKENS:
                mods.add(part)
                continue

            if part in MOUSE_TOKENS:
                self.registry.mouse_actions[normalized_hotkey] = func
                return

            main_scan = get_scan_code_for_key(self.app.layout, part)
            if main_scan is None:
                try:
                    codes = keyboard.key_to_scan_codes(part)
                    if codes:
                        main_scan = codes[0]
                except Exception:
                    main_scan = None

        if main_scan is not None:
            self.registry.keyboard_actions[(frozenset(mods), main_scan)] = func

    def _register_global_hook(self) -> None:
        if self._hook_active:
            return
        try:
            keyboard.hook(self.global_hook_listener)
            self._hook_active = True
        except Exception:
            self._hook_active = False

    def global_hook_listener(self, event) -> None:
        if event.event_type != keyboard.KEY_DOWN:
            return

        current_mods = self.app.get_current_modifiers()
        action = self.registry.keyboard_actions.get((frozenset(current_mods), event.scan_code))
        if action is None:
            return

        def safe_execute():
            self.app.release_modifiers()
            try:
                action()
            finally:
                time.sleep(0.05)
                self.app.restore_modifiers(current_mods)

        threading.Thread(target=safe_execute, daemon=True).start()


class NotificationService:
    def __init__(self, app: "OrganizerApp") -> None:
        self.app = app
        self._running = False

    def start(self) -> None:
        if not WINSDK_AVAILABLE:
            safe_print("[INFO] Notification listener disabled: WinRT packages not available.")
            return

        if self._running:
            return

        self._running = True
        threading.Thread(target=self._run_async_loop, daemon=True).start()

    def stop(self) -> None:
        self._running = False

    def _run_async_loop(self) -> None:
        try:
            import pythoncom

            try:
                pythoncom.CoInitializeEx(0, pythoncom.COINIT_MULTITHREADED)
            except Exception:
                pass

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.poll_notifications())
        except Exception as exc:
            safe_print(f"[WARN] Notification listener stopped: {exc}")

    async def poll_notifications(self) -> None:
        if not WINSDK_AVAILABLE or UserNotificationListener is None:
            return

        try:
            listener = UserNotificationListener.current
            access = await listener.request_access_async()
        except Exception as exc:
            safe_print(f"[WARN] Could not initialize Windows notification listener: {exc}")
            return

        if access != 1:
            return

        seen_ids: set[int] = set()
        first_pass = True

        while self._running:
            try:
                is_retro = self.app.config.data.get("game_version", "Unity") == "Rétro"
                is_autofocus_on = self.app.config.data.get("auto_focus_retro", False)

                notifications = await listener.get_notifications_async(NotificationKinds.TOAST)
                current_ids: set[int] = set()

                for notif in notifications:
                    current_ids.add(notif.id)
                    if notif.id in seen_ids:
                        continue

                    seen_ids.add(notif.id)

                    if first_pass or not is_retro or not is_autofocus_on:
                        continue

                    try:
                        binding = notif.notification.visual.bindings[0]
                        texts = [text_element.text for text_element in binding.get_text_elements()]
                    except Exception:
                        continue

                    for line in texts:
                        if " - Dofus Retro" not in line:
                            continue

                        pseudo = line.split(" - ")[0].strip()
                        cycle_list = self.app.logic.get_cycle_list()

                        for index, acc in enumerate(cycle_list):
                            if acc["name"] == pseudo:
                                self.app.gui.root.after(0, self.app.logic.focus_window, acc["hwnd"])
                                self.app.current_idx = index
                                break
                        break

                seen_ids.intersection_update(current_ids)
                first_pass = False

            except Exception:
                pass

            await asyncio.sleep(NOTIFICATION_POLL_INTERVAL)


class OrganizerApp:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.logic = DofusLogic(self.config)
        self.gui = OrganizerGUI(self)

        self.current_idx = 0
        self._listener_running = True

        self.tray_service = TrayService(self)
        self.hotkey_service = HotkeyService(self)
        self.notification_service = NotificationService(self)

        self.radial_focus = RadialMenu(
            self.gui.root,
            self.on_radial_focus_select,
            accent_color="#2ecc71",
            hover_color="#27ae60",
            center_icon_path=resource_path("skin", "character.png"),
        )

        saved_volume = self.config.data.get("volume_level", 50) / 100.0
        self.radial_focus.set_base_volume(saved_volume)

        self.setup_hotkeys()
        self.refresh()

        self.notification_service.start()
        self.tray_service.start()

        threading.Thread(target=self.background_listener, daemon=True).start()

        self.gui.root.after(1000, self.check_conflicting_software)
        if not self.config.data.get("tutorial_done", False):
            self.gui.root.after(800, self.gui.launch_tutorial)

    @property
    def layout(self) -> str:
        return self.config.data.get("keyboard_layout", "qwerty")

    def _t(self, text, **kwargs):
        return tr(self.config, text, **kwargs)

    def restart_app(self) -> None:
        self.shutdown_services()

        try:
            self.gui.root.withdraw()
            self.gui.root.update_idletasks()
            self.gui.root.destroy()
        except Exception:
            pass

        if getattr(sys, "frozen", False):
            os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
        else:
            script = os.path.abspath(sys.argv[0])
            os.execv(sys.executable, [sys.executable, script, *sys.argv[1:]])

    def shutdown_services(self) -> None:
        self._listener_running = False
        self.notification_service.stop()
        self.tray_service.stop()
        self.hotkey_service.reset()

    def apply_advanced_modifier(self, bind_str: str) -> str:
        if not bind_str:
            return ""

        parts = [normalize_key_name(part) for part in str(bind_str).split("+") if part]
        if not parts:
            return ""

        base_parts = [part for part in parts if part not in MODIFIER_TOKENS]
        if not base_parts:
            return ""

        mod = normalize_key_name(self.config.data.get("advanced_bind_modifier", "ctrl"))
        if mod in {"", "none", "aucun", "nenhum"}:
            return "+".join(base_parts)
        if mod not in MODIFIER_TOKENS:
            mod = "ctrl"

        return "+".join([mod] + base_parts)

    def setup_hotkeys(self) -> None:
        self.hotkey_service.rebuild()

    def refresh(self) -> None:
        slots = self.logic.scan_slots()
        self.gui.root.after(0, self.gui.refresh_list, slots)

    def update_volume(self, volume_val: int) -> None:
        self.config.data["volume_level"] = volume_val
        safe_config_save(self.config)
        self.radial_focus.set_base_volume(volume_val / 100.0)

    def toggle_window_visibility(self) -> None:
        try:
            if self.gui.root.state() == "withdrawn":
                self.gui.root.deiconify()
                self.gui.root.lift()
                self.gui.root.focus_force()
            else:
                self.gui.root.withdraw()
        except Exception:
            pass

    def get_vk(self, key_str: str) -> Optional[int]:
        key_str = normalize_key_name(key_str)
        mapping = {
            "alt": win32con.VK_MENU,
            "ctrl": win32con.VK_CONTROL,
            "shift": win32con.VK_SHIFT,
            "left_click": 0x01,
            "right_click": 0x02,
            "middle_click": 0x04,
            "mouse4": 0x05,
            "mouse5": 0x06,
        }

        if key_str in mapping:
            return mapping[key_str]

        scan_code = get_scan_code_for_key(self.layout, key_str)
        if scan_code is not None:
            try:
                vk = ctypes.windll.user32.MapVirtualKeyW(scan_code, 1)
                if vk:
                    return vk
            except Exception:
                pass

        if len(key_str) == 1:
            return ord(key_str.upper())

        if key_str.startswith("f") and key_str[1:].isdigit():
            return 0x6F + int(key_str[1:])

        return None

    def is_hotkey_pressed(self, hotkey_str: str) -> bool:
        if not hotkey_str:
            return False

        for part in hotkey_str.split("+"):
            vk = self.get_vk(part)
            if vk is None or win32api.GetAsyncKeyState(vk) >= 0:
                return False
        return True

    def get_current_modifiers(self) -> set[str]:
        mods: set[str] = set()

        if win32api.GetAsyncKeyState(win32con.VK_CONTROL) < 0:
            mods.add("ctrl")
        if win32api.GetAsyncKeyState(win32con.VK_MENU) < 0:
            mods.add("alt")
        if win32api.GetAsyncKeyState(win32con.VK_SHIFT) < 0:
            mods.add("shift")

        return mods

    def release_modifiers(self) -> None:
        try:
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

    def restore_modifiers(self, mods: set[str]) -> None:
        try:
            if "alt" in mods:
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
            if "ctrl" in mods:
                win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            if "shift" in mods:
                win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
        except Exception:
            pass

    def execute_advanced_and_update(self, mode: str, identifier) -> None:
        new_idx = self.logic.execute_advanced_bind(mode, identifier)
        if new_idx != -1:
            self.current_idx = new_idx

    def on_radial_focus_select(self, target_name: str) -> None:
        for acc in self.logic.all_accounts:
            if acc["name"] == target_name:
                self.logic.focus_window(acc["hwnd"])
                break

        cycle_list = self.logic.get_cycle_list()
        for index, acc in enumerate(cycle_list):
            if acc["name"] == target_name:
                self.current_idx = index
                break

    def sync_current_idx_with_foreground(self) -> None:
        try:
            foreground_hwnd = win32gui.GetForegroundWindow()
            cycle_list = self.logic.get_cycle_list()
            for index, acc in enumerate(cycle_list):
                if acc["hwnd"] == foreground_hwnd:
                    self.current_idx = index
                    break
        except Exception:
            pass

    def process_mouse_hotkeys(self) -> None:
        for hotkey_str, func in self.hotkey_service.registry.mouse_actions.items():
            is_pressed = self.is_hotkey_pressed(hotkey_str)
            was_pressed = self.hotkey_service.registry.mouse_states.get(hotkey_str, False)

            if is_pressed and not was_pressed:
                self.hotkey_service.registry.mouse_states[hotkey_str] = True

                def safe_mouse_execute(action=func):
                    self.release_modifiers()
                    action()

                threading.Thread(target=safe_mouse_execute, daemon=True).start()

            elif not is_pressed and was_pressed:
                self.hotkey_service.registry.mouse_states[hotkey_str] = False

    def process_radial_menu(self, radial_was_open: bool) -> bool:
        radial_hotkey = self.config.data.get("radial_menu_hotkey", "")
        radial_active = self.config.data.get("radial_menu_active", True)

        if not radial_active or not radial_hotkey:
            if radial_was_open:
                self.gui.root.after(0, self.radial_focus.hide)
            return False

        is_pressed = self.is_hotkey_pressed(radial_hotkey)

        if is_pressed and not radial_was_open:
            is_retro = self.config.data.get("game_version", "Unity") == "Rétro"

            active_accounts = []
            for acc in self.logic.get_cycle_list():
                current_class = acc.get("classe", "Inconnu")
                if is_retro and current_class != "Inconnu":
                    current_class = f"{current_class}_retro"

                active_accounts.append(
                    {
                        "name": acc["name"],
                        "classe": current_class,
                        "hwnd": acc["hwnd"],
                    }
                )

            foreground_hwnd = win32gui.GetForegroundWindow()
            current_name = None
            for acc in active_accounts:
                if acc["hwnd"] == foreground_hwnd:
                    current_name = acc["name"]
                    break

            x_pos, y_pos = win32api.GetCursorPos()
            self.gui.root.after(
                0,
                self.radial_focus.show,
                x_pos,
                y_pos,
                active_accounts,
                current_name,
                is_retro,
            )
            return True

        if radial_was_open and not is_pressed:
            self.gui.root.after(0, self.radial_focus.hide)
            return False

        return radial_was_open

    def background_listener(self) -> None:
        radial_was_open = False

        while self._listener_running:
            self.process_mouse_hotkeys()
            radial_was_open = self.process_radial_menu(radial_was_open)
            self.sync_current_idx_with_foreground()
            time.sleep(DEFAULT_POLL_INTERVAL)

    def focus_leader(self) -> None:
        if not self.logic.leader_hwnd:
            return

        self.logic.focus_window(self.logic.leader_hwnd)

        cycle_list = self.logic.get_cycle_list()
        leader_name = self.config.data.get("leader_name", "")

        for index, acc in enumerate(cycle_list):
            if acc["name"] == leader_name:
                self.current_idx = index
                break

    def next_char(self) -> None:
        cycle_list = self.logic.get_cycle_list()
        if not cycle_list:
            return

        self.current_idx = (self.current_idx + 1) % len(cycle_list)
        self.logic.focus_window(cycle_list[self.current_idx]["hwnd"])

    def prev_char(self) -> None:
        cycle_list = self.logic.get_cycle_list()
        if not cycle_list:
            return

        self.current_idx = (self.current_idx - 1) % len(cycle_list)
        self.logic.focus_window(cycle_list[self.current_idx]["hwnd"])

    def check_conflicting_software(self) -> None:
        if self.config.data.get("ignore_organizer_warning", False):
            return

        try:
            output = os.popen('tasklist /FI "IMAGENAME eq organizer.exe" /NH').read().lower()
            if "organizer.exe" in output:
                self.show_conflict_popup()
        except Exception:
            pass

    def show_conflict_popup(self) -> None:
        popup = ctk.CTkToplevel(self.gui.root)
        popup.title(self._t("⚠️ Conflit de logiciels détecté"))
        popup.geometry("480x250")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        popup.transient(self.gui.root)

        popup.update_idletasks()
        x_pos = self.gui.root.winfo_x() + (self.gui.root.winfo_width() // 2) - (480 // 2)
        y_pos = self.gui.root.winfo_y() + (self.gui.root.winfo_height() // 2) - (250 // 2)
        popup.geometry(f"+{x_pos}+{y_pos}")

        msg = self._t(
            "Le logiciel 'Organizer' est actuellement ouvert.\n"
            "L'utilisation de deux gestionnaires de pages simultanément\n"
            "va créer des bugs et des conflits de focus sur DOSOFT.\n\n"
            "Nous vous recommandons fortement de le fermer."
        )

        ctk.CTkLabel(
            popup,
            text=msg,
            justify="center",
            font=ctk.CTkFont(size=13),
        ).pack(pady=(20, 15))

        var_ignore = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            popup,
            text=self._t("Ne plus m'afficher cet avertissement"),
            variable=var_ignore,
        ).pack(pady=(0, 20))

        frame_btn = ctk.CTkFrame(popup, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20)

        def on_close_organizer():
            if var_ignore.get():
                self.config.data["ignore_organizer_warning"] = True
                safe_config_save(self.config)

            os.system("taskkill /F /IM organizer.exe /T")
            popup.destroy()
            self.gui.show_temporary_message(
                self._t("✅ Organizer fermé avec succès !"),
                "#2ecc71",
            )

        def on_keep_organizer():
            if var_ignore.get():
                self.config.data["ignore_organizer_warning"] = True
                safe_config_save(self.config)
            popup.destroy()

        ctk.CTkButton(
            frame_btn,
            text=self._t("Fermer Organizer"),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            command=on_close_organizer,
        ).pack(side="left", expand=True, padx=10)

        ctk.CTkButton(
            frame_btn,
            text=self._t("Conserver"),
            fg_color="#7f8c8d",
            hover_color="#95a5a6",
            command=on_keep_organizer,
        ).pack(side="right", expand=True, padx=10)

        popup.grab_set()

    def quit_app(self) -> None:
        self.shutdown_services()
        my_pid = os.getpid()
        os.system(f"taskkill /F /PID {my_pid} /T")


def check_version(app_config: Config) -> None:
    try:
        response = requests.get(VERSION_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        latest_version = data.get("version")

        if latest_version and latest_version != APP_VERSION:
            message = t_cfg(
                app_config,
                "Une mise à jour est requise pour utiliser le logiciel.\n\n"
                "Votre version : {current_version}\n"
                "Version disponible : {latest_version}\n\n"
                "Mise à jour dispo sur Dosoft.fr",
                current_version=APP_VERSION,
                latest_version=latest_version,
            )
            ctypes.windll.user32.MessageBoxW(
                0,
                message,
                t_cfg(app_config, "Mise à jour requise"),
                0x10,
            )
    except requests.RequestException:
        ctypes.windll.user32.MessageBoxW(
            0,
            t_cfg(app_config, "Impossible de vérifier la version."),
            t_cfg(app_config, "Erreur réseau"),
            0x10,
        )


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_as_admin() -> None:
    if getattr(sys, "frozen", False):
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join(sys.argv[1:]),
            None,
            1,
        )
        return

    script = os.path.abspath(sys.argv[0])
    params = " ".join(f'"{arg}"' for arg in sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        f'"{script}" {params}',
        None,
        1,
    )


def handle_multiple_instances(app_config: Config):
    mutex_name = "DOSOFT_SINGLE_INSTANCE_MUTEX"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)

    if ctypes.windll.kernel32.GetLastError() != 183:
        return mutex

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    reply = messagebox.askyesno(
        t_cfg(app_config, "Instance détectée"),
        t_cfg(
            app_config,
            "Une instance de DOSOFT est déjà en cours d'exécution !\n\nVoulez-vous fermer l'ancienne instance pour ouvrir celle-ci ?",
        ),
        parent=root,
    )

    if reply:
        hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
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
        return mutex

    root.destroy()
    sys.exit(0)


def start_application() -> None:
    if not is_admin():
        run_as_admin()
        sys.exit()

    app_config = Config()
    _app_mutex = handle_multiple_instances(app_config)
    check_version(app_config)

    app = OrganizerApp(app_config)
    app.gui.run()


if __name__ == "__main__":
    start_application()