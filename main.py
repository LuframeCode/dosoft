import os
import sys
import ctypes
import threading
import keyboard
import time
import win32api
import win32con
import win32gui
import win32process
from PIL import Image
import tkinter as tk
import customtkinter as ctk
import pystray
from pystray import MenuItem as item
import asyncio
import requests
from tkinter import messagebox 

# --- FORCAGE DU DPI AWARENESS (Règle les soucis 4K / Zoom Windows) ---
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except: pass

try:
    from winrt.windows.ui.notifications.management import UserNotificationListener
    from winrt.windows.ui.notifications import NotificationKinds
    WINSDK_AVAILABLE = True
except ImportError:
    WINSDK_AVAILABLE = False

from config_manager import Config
from logic import DofusLogic
from gui import OrganizerGUI
from radial_menu import RadialMenu
from i18n_manager import I18nManager
from keyboard_layout_manager import KeyboardLayoutManager


def try_load_windows_layout(layout_name):
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


class OrganizerApp:
    def __init__(self):
        self.config = Config()
        self.i18n = I18nManager(self.config.data.get("language", "fr"))
        self.keymaps = KeyboardLayoutManager(self.config.data.get("keyboard_layout", "azerty_fr"))
        try_load_windows_layout(self.config.data.get("keyboard_layout", "azerty_fr"))
        self.logic = DofusLogic(self.config)
        self.gui = OrganizerGUI(self)
        self.current_idx = 0
        self.hotkey_actions = {} 
        self.mouse_hotkeys = {}
        self.mouse_states = {}
        
        self.radial_focus = RadialMenu(self.gui.root, self.on_radial_focus_select, accent_color="#2ecc71", hover_color="#27ae60", center_icon_path="skin/character.png")
        
        saved_vol = self.config.data.get("volume_level", 50) / 100.0
        self.radial_focus.set_base_volume(saved_vol)
        
        threading.Thread(target=self.background_listener, daemon=True).start()
        
        self.setup_hotkeys()
        self.refresh()
        self.start_notification_listener()
        self.setup_system_tray()
        
        self.gui.root.after(1000, self.check_conflicting_software)

        if not self.config.data.get("tutorial_done", False):
            self.gui.root.after(800, self.gui.launch_tutorial)
    
    def setup_system_tray(self):
        icon_path = "logo.ico" 
        try: image = Image.open(icon_path)
        except: image = Image.new('RGB', (64, 64), color=(44, 62, 80))

        menu = pystray.Menu(
            item('Afficher/Cacher', self.toggle_from_tray, default=True),
            item('Trier Barre Windows', self.sort_taskbar_from_tray),
            item('Rafraîchir', self.refresh_from_tray),
            item('Quitter', self.quit_from_tray)
        )
        self.tray_icon = pystray.Icon("dosoft_tray", image, "DOSOFT", menu)
        self.tray_icon.run_detached()

    def toggle_from_tray(self, icon, item):
        def safe_toggle():
            if self.gui.root.state() == 'withdrawn':
                self.gui.root.deiconify()
                self.gui.root.lift()
                self.gui.root.focus_force()
            else:
                self.gui.root.withdraw()
        self.gui.root.after(0, safe_toggle)

    def refresh_from_tray(self, icon, item):
        self.gui.root.after(0, self.refresh)

    def sort_taskbar_from_tray(self, icon, item):
        self.gui.root.after(0, self.gui.trigger_sort_taskbar)

    def quit_from_tray(self, icon, item):
        self.tray_icon.stop() 
        self.gui.root.after(0, self.gui.root.destroy) 

    def update_volume(self, volume_val):
        self.config.data["volume_level"] = volume_val
        self.config.save()
        vol_float = volume_val / 100.0
        self.radial_focus.set_base_volume(vol_float)

    def check_conflicting_software(self):
        if self.config.data.get("ignore_organizer_warning", False):
            return
        try:
            output = os.popen('tasklist /FI "IMAGENAME eq organizer.exe" /NH').read().lower()
            if "organizer.exe" in output:
                self.show_conflict_popup()
        except Exception: pass

    def show_conflict_popup(self):
        popup = ctk.CTkToplevel(self.gui.root)
        popup.title("⚠️ Conflit de logiciels détecté")
        popup.geometry("480x250")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        popup.transient(self.gui.root)
        
        popup.update_idletasks()
        x = self.gui.root.winfo_x() + (self.gui.root.winfo_width() // 2) - (480 // 2)
        y = self.gui.root.winfo_y() + (self.gui.root.winfo_height() // 2) - (250 // 2)
        popup.geometry(f"+{x}+{y}")

        msg = ("Le logiciel 'Organizer' est actuellement ouvert.\n"
               "L'utilisation de deux gestionnaires de pages simultanément\n"
               "va créer des bugs et des conflits de focus sur DOSOFT.\n\n"
               "Nous vous recommandons fortement de le fermer.")
        
        lbl = ctk.CTkLabel(popup, text=msg, justify="center", font=ctk.CTkFont(size=13))
        lbl.pack(pady=(20, 15))

        var_ignore = ctk.BooleanVar(value=False)
        chk = ctk.CTkCheckBox(popup, text="Ne plus m'afficher cet avertissement", variable=var_ignore)
        chk.pack(pady=(0, 20))

        frame_btn = ctk.CTkFrame(popup, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20)

        def on_close_organizer():
            if var_ignore.get():
                self.config.data["ignore_organizer_warning"] = True
                self.config.save()
            os.system("taskkill /F /IM organizer.exe /T")
            popup.destroy()
            self.gui.show_temporary_message("✅ Organizer fermé avec succès !", "#2ecc71")

        def on_keep_organizer():
            if var_ignore.get():
                self.config.data["ignore_organizer_warning"] = True
                self.config.save()
            popup.destroy()

        btn_close = ctk.CTkButton(frame_btn, text="Fermer Organizer", fg_color="#27ae60", hover_color="#2ecc71", command=on_close_organizer)
        btn_close.pack(side="left", expand=True, padx=10)

        btn_keep = ctk.CTkButton(frame_btn, text="Conserver", fg_color="#7f8c8d", hover_color="#95a5a6", command=on_keep_organizer)
        btn_keep.pack(side="right", expand=True, padx=10)
        
        popup.grab_set()

    def get_vk(self, key_str):
        key_str = key_str.lower().strip()
        mapping = {
            "alt": win32con.VK_MENU, "ctrl": win32con.VK_CONTROL, "shift": win32con.VK_SHIFT,
            "left_click": 0x01, "right_click": 0x02, "middle_click": 0x04,
            "mouse4": 0x05, "mouse5": 0x06
        }
        if key_str in mapping: return mapping[key_str]
        
        scan_code = self.keymaps.key_to_scan(key_str)
        if scan_code is not None:
            vk = ctypes.windll.user32.MapVirtualKeyW(scan_code, 1) 
            if vk: return vk
            
        if len(key_str) == 1: return ord(key_str.upper())
        if key_str.startswith('f') and key_str[1:].isdigit():
            return 0x6F + int(key_str[1:])
        return None

    def is_hotkey_pressed(self, hk_str):
        if not hk_str: return False
        parts = hk_str.split('+')
        for p in parts:
            token = p.lower().strip()
            if token in {"ctrl", "alt", "shift"}:
                vk = self.get_vk(token)
                if vk is None or win32api.GetAsyncKeyState(vk) >= 0:
                    return False
                continue

            mouse_vk = self.get_vk(token) if "click" in token or "mouse" in token else None
            if mouse_vk is not None:
                if win32api.GetAsyncKeyState(mouse_vk) >= 0:
                    return False
                continue

            scan_code = self.keymaps.resolve_scan_code(token)
            if scan_code is not None:
                if not keyboard.is_pressed(scan_code):
                    return False
            elif not keyboard.is_pressed(token):
                return False
        return True

    def background_listener(self):
        radial_was_open = False
        
        while True:
            # Gestion des macros de souris (MB4, MB5, Clics)
            if hasattr(self, 'mouse_hotkeys'):
                for hk_str, func in self.mouse_hotkeys.items():
                    is_pressed = self.is_hotkey_pressed(hk_str)
                    was_pressed = self.mouse_states.get(hk_str, False)
                    
                    if is_pressed and not was_pressed:
                        self.mouse_states[hk_str] = True
                        def safe_mouse_execute(f=func):
                            self.release_modifiers()
                            f()
                        threading.Thread(target=safe_mouse_execute, daemon=True).start()
                    elif not is_pressed and was_pressed:
                        self.mouse_states[hk_str] = False

            # Gestion de la roue radiale
            radial_hk = self.config.data.get("radial_menu_hotkey", "")
            radial_active = self.config.data.get("radial_menu_active", True)
            
            if radial_active and radial_hk:
                is_pressed = self.is_hotkey_pressed(radial_hk)
                
                if is_pressed and not radial_was_open:
                    radial_was_open = True
                    is_retro = self.config.data.get("game_version", "Unity") == "Rétro"
                    
                    # Préparation des têtes Retro ou Unity
                    active_accs = []
                    for acc in self.logic.get_cycle_list():
                        cls = acc.get('classe', 'Inconnu')
                        if is_retro and cls != "Inconnu": cls = f"{cls}_retro"
                        active_accs.append({'name': acc['name'], 'classe': cls, 'hwnd': acc['hwnd']})
                    
                    fg_hwnd = win32gui.GetForegroundWindow()
                    current_name = None
                    for acc in active_accs:
                        if acc['hwnd'] == fg_hwnd:
                            current_name = acc['name']
                            break
                            
                    x, y = win32api.GetCursorPos()
                    self.gui.root.after(0, self.radial_focus.show, x, y, active_accs, current_name)
                    
                elif radial_was_open and not is_pressed:
                    radial_was_open = False
                    self.gui.root.after(0, self.radial_focus.hide)

            # Synchronisation de l'index au clic manuel
            try:
                fg_hwnd = win32gui.GetForegroundWindow()
                cycle_list = self.logic.get_cycle_list()
                if cycle_list:
                    for index, acc in enumerate(cycle_list):
                        if acc['hwnd'] == fg_hwnd:
                            if self.current_idx != index:
                                self.current_idx = index
                            break
            except Exception: pass
            time.sleep(0.01)

    def on_radial_focus_select(self, target_name):
        for acc in self.logic.all_accounts:
            if acc['name'] == target_name:
                self.logic.focus_window(acc['hwnd'])
                break
        
        cycle_list = self.logic.get_cycle_list()
        for index, acc in enumerate(cycle_list):
            if acc['name'] == target_name:
                self.current_idx = index
                break

    def register_action(self, hk_str, func):
        if not hk_str: return
        hk_str = hk_str.lower().strip()
        
        if 'click' in hk_str or 'mouse' in hk_str:
            self.mouse_hotkeys[hk_str] = func
            return
            
        parts = hk_str.split('+')
        mods = set()
        main_scan = None
        for p in parts:
            if p in ['ctrl', 'alt', 'shift']:
                mods.add(p)
                continue
            main_scan = self.keymaps.resolve_scan_code(p)
        if main_scan is not None:
            self.hotkey_actions[(frozenset(mods), main_scan)] = func

    def _execute_advanced_and_update(self, mode, identifier):
        new_idx = self.logic.execute_advanced_bind(mode, identifier)
        if new_idx != -1: 
            self.current_idx = new_idx

    def release_modifiers(self):
        """Force Windows à relâcher les touches Ctrl, Alt et Shift après la saisie."""
        try:
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
        except: pass

    def restore_modifiers(self, mods):
        try:
            if 'alt' in mods: win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
            if 'ctrl' in mods: win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            if 'shift' in mods: win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
        except: pass

    def global_hook_listener(self, event):
        if event.event_type != keyboard.KEY_DOWN: return
        
        current_mods = set()
        if win32api.GetAsyncKeyState(win32con.VK_CONTROL) < 0: current_mods.add('ctrl')
        if win32api.GetAsyncKeyState(win32con.VK_MENU) < 0: current_mods.add('alt')
        if win32api.GetAsyncKeyState(win32con.VK_SHIFT) < 0: current_mods.add('shift')
        
        key = (frozenset(current_mods), event.scan_code)
        if key in self.hotkey_actions:
            def safe_execute(mods=current_mods):
                self.release_modifiers()
                self.hotkey_actions[key]()
                time.sleep(0.05)
                self.restore_modifiers(mods)
            threading.Thread(target=safe_execute, daemon=True).start()

    def setup_hotkeys(self):
        keyboard.unhook_all()
        self.hotkey_actions = {} 
        self.mouse_hotkeys = {} 
        self.mouse_states = {}  
        
        self.register_action('f5', self.refresh)
        self.register_action('f12', self.quit_app)
        
        cfg = self.config.data 
        
        # Binds avancés dynamiques
        mode = cfg.get("advanced_bind_mode", "cycle")
        if mode == "cycle":
            row_binds = cfg.get("cycle_row_binds", [])
            for index, bind_str in enumerate(row_binds):
                if bind_str:
                    self.register_action(bind_str, lambda idx=index: self._execute_advanced_and_update("cycle", idx))
        elif mode == "bind":
            char_binds = cfg.get("persistent_character_binds", {})
            for pseudo, bind_str in char_binds.items():
                if bind_str:
                    self.register_action(bind_str, lambda ps=pseudo: self._execute_advanced_and_update("bind", ps))
                    
        try:
            if cfg.get("prev_key"): self.register_action(cfg["prev_key"], self.prev_char)
            if cfg.get("next_key"): self.register_action(cfg["next_key"], self.next_char)
            if cfg.get("leader_key"): self.register_action(cfg["leader_key"], self.focus_leader)
            if cfg.get("toggle_app_key"): self.register_action(cfg["toggle_app_key"], lambda: self.gui.root.after(0, self.gui.toggle_visibility))
            keyboard.hook(self.global_hook_listener)
        except Exception: pass

    def refresh(self): 
        slots = self.logic.scan_slots()
        self.gui.root.after(0, self.gui.refresh_list, slots)
    
    def focus_leader(self):
        if self.logic.leader_hwnd: 
            self.logic.focus_window(self.logic.leader_hwnd)
            cycle_list = self.logic.get_cycle_list()
            leader_name = self.config.data.get("leader_name", "")
            for index, acc in enumerate(cycle_list):
                if acc['name'] == leader_name:
                    self.current_idx = index
                    break

    def next_char(self):
        cycle_list = self.logic.get_cycle_list()
        if not cycle_list: return
        self.current_idx = (self.current_idx + 1) % len(cycle_list)
        self.logic.focus_window(cycle_list[self.current_idx]['hwnd'])

    def prev_char(self):
        cycle_list = self.logic.get_cycle_list()
        if not cycle_list: return
        self.current_idx = (self.current_idx - 1) % len(cycle_list)
        self.logic.focus_window(cycle_list[self.current_idx]['hwnd'])

    def quit_app(self):
        my_pid = os.getpid()
        os.system(f"taskkill /F /PID {my_pid} /T")

    def start_notification_listener(self):
        if not WINSDK_AVAILABLE: return

        def run_async_loop():
            try:
                import pythoncom
                pythoncom.CoInitializeEx(0, pythoncom.COINIT_MULTITHREADED)
            except: pass
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.poll_notifications())

        threading.Thread(target=run_async_loop, daemon=True).start()

    async def poll_notifications(self):
        listener = UserNotificationListener.current
        access = await listener.request_access_async()
        if access != 1: return

        seen_ids = set()
        first_pass = True 

        while True:
            try:
                is_retro = self.config.data.get("game_version", "Unity") == "Rétro"
                is_autofocus_on = self.config.data.get("auto_focus_retro", False)
                
                notifs = await listener.get_notifications_async(NotificationKinds.TOAST)
                current_ids = set()
                
                for n in notifs:
                    current_ids.add(n.id)
                    if n.id not in seen_ids:
                        seen_ids.add(n.id)
                        if not first_pass and is_retro and is_autofocus_on:
                            try:
                                binding = n.notification.visual.bindings[0]
                                texts = [t.text for t in binding.get_text_elements()]
                                for ligne in texts:
                                    if " - Dofus Retro" in ligne:
                                        pseudo = ligne.split(" - ")[0].strip()
                                        cycle_list = self.logic.get_cycle_list()
                                        for index, acc in enumerate(cycle_list):
                                            if acc['name'] == pseudo:
                                                self.gui.root.after(0, self.logic.focus_window, acc['hwnd'])
                                                self.current_idx = index
                                                break
                                        break 
                            except Exception: pass
                seen_ids.intersection_update(current_ids)
                first_pass = False 
            except Exception: pass
            await asyncio.sleep(0.5) 
                
# --- SYSTÈME DE VÉRIFICATION DE VERSION ---
CURRENT_VERSION = "1.1.1" 
VERSION_URL = "https://raw.githubusercontent.com/LuframeCode/Dosoft/main/version.json"

def check_version():
    try:
        response = requests.get(VERSION_URL, timeout=5)
        response.raise_for_status() 
        data = response.json()
        latest_version = data.get("version")

        if latest_version and latest_version != CURRENT_VERSION:
            message = (
                f"Une mise à jour est requise pour utiliser le logiciel.\n\n"
                f"Votre version : {CURRENT_VERSION}\n"
                f"Version disponible : {latest_version}\n\n"
                f"Mise à jour dispo sur Dosoft.fr"
            )
            ctypes.windll.user32.MessageBoxW(0, message, "Mise à jour requise", 0x10)
    except requests.RequestException:
        ctypes.windll.user32.MessageBoxW(0, "Impossible de vérifier la version.", "Erreur réseau", 0x10)
        

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def run_as_admin():
    if getattr(sys, 'frozen', False):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
    else:
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)

def handle_multiple_instances():
    mutex_name = "DOSOFT_SINGLE_INSTANCE_MUTEX"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        rep = messagebox.askyesno("Instance détectée", "Une instance de DOSOFT est déjà en cours d'exécution !\n\nVoulez-vous fermer l'ancienne instance pour ouvrir celle-ci ?", parent=root)
        if rep:
            hwnd = win32gui.FindWindow(None, "DOSOFT v1.1.1")
            if hwnd:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
                    ctypes.windll.kernel32.TerminateProcess(handle, 0)
                    ctypes.windll.kernel32.CloseHandle(handle)
                except: pass
            time.sleep(0.5) 
            root.destroy()
        else:
            root.destroy()
            sys.exit(0)
    return mutex

def start_application():
    if not is_admin():
        run_as_admin()
        sys.exit() 
           
    _app_mutex = handle_multiple_instances()
    check_version()

    app = OrganizerApp()
    app.gui.run()

if __name__ == "__main__":
    start_application()
