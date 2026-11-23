import os
import sys
import threading
import time
import customtkinter as ctk
import requests
import platform_backend as pb
from app_version import CURRENT_VERSION, APP_TITLE

# DPI (Windows) / dossier des ressources (macOS)
pb.prepare_process()

from config_manager import Config
from logic import DofusLogic
from gui import OrganizerGUI
from radial_menu import RadialMenu
from i18n_manager import I18nManager
from keyboard_layout_manager import KeyboardLayoutManager


class OrganizerApp:
    def __init__(self):
        self.config = Config()
        self.i18n = I18nManager(self.config.data.get("language", "fr"))
        self.keymaps = KeyboardLayoutManager(self.config.data.get("keyboard_layout", "azerty_fr"))
        pb.load_system_keyboard_layout(self.config.data.get("keyboard_layout", "azerty_fr"))
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
        pb.install_app_handlers(self.gui.root, on_reopen=self.show_main_window, on_quit=self.quit_app)
        if pb.permissions_supported():
            self.gui.root.after(1200, self.check_mac_permissions)

        if not self.config.data.get("tutorial_done", False):
            self.gui.root.after(800, self.gui.launch_tutorial)
    
    def setup_system_tray(self):
        sort_label = self.i18n.t("tray_sort_mac", "Trier les fenêtres") if pb.IS_MAC else self.i18n.t("tray_sort", "Trier Barre Windows")
        menu_items = [
            (self.i18n.t("tray_toggle", "Afficher/Cacher"), self.toggle_from_tray, True),
            (sort_label, self.sort_taskbar_from_tray, False),
            (self.i18n.t("tray_refresh", "Rafraîchir"), self.refresh_from_tray, False),
            (self.i18n.t("tray_quit", "Quitter"), self.quit_from_tray, False),
        ]
        try:
            self.tray_icon = pb.create_tray(self.gui.root, "DOSOFT", "logo.ico", menu_items)
        except Exception:
            self.tray_icon = None

    def show_main_window(self):
        self.gui.root.deiconify()
        self.gui.root.lift()
        self.gui.root.focus_force()
        pb.bring_app_to_front()
        self.gui.is_visible = True

    def toggle_from_tray(self):
        def safe_toggle():
            if self.gui.root.state() == 'withdrawn':
                self.show_main_window()
            else:
                self.gui.root.withdraw()
                self.gui.is_visible = False
        self.gui.root.after(0, safe_toggle)

    def refresh_from_tray(self):
        self.gui.root.after(0, self.refresh)

    def sort_taskbar_from_tray(self):
        self.gui.root.after(0, self.gui.trigger_sort_taskbar)

    def quit_from_tray(self):
        if self.tray_icon is not None:
            self.tray_icon.stop()
        if pb.IS_MAC:
            self.quit_app()
        else:
            self.gui.root.after(0, self.gui.root.destroy)

    def check_mac_permissions(self):
        """macOS : vérifie la permission Accessibilité (raccourcis, focus, titres de fenêtres)."""
        perms = pb.check_permissions()
        if all(perms.values()):
            return
        self.show_permissions_popup()

    def show_permissions_popup(self):
        if getattr(self, "_perm_popup", None) is not None and self._perm_popup.winfo_exists():
            return
        popup = ctk.CTkToplevel(self.gui.root)
        self._perm_popup = popup
        popup.title(self.i18n.t("popup_permissions_title", "🔐 Autorisation requise"))
        popup.geometry("520x300")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)

        msg = self.i18n.t(
            "popup_permissions_text",
            "DOSOFT a besoin de l'autorisation « Accessibilité » de macOS pour :\n"
            "• lire le nom des personnages (titres des fenêtres Dofus)\n"
            "• passer d'une fenêtre à l'autre\n"
            "• utiliser les raccourcis clavier / souris globaux\n\n"
            "Réglages Système → Confidentialité et sécurité → Accessibilité,\n"
            "puis cochez DOSOFT. Les raccourcis s'activent automatiquement."
        )
        ctk.CTkLabel(popup, text=msg, justify="left", font=ctk.CTkFont(size=13)).pack(padx=20, pady=(20, 15))
        lbl_status = ctk.CTkLabel(popup, text="", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_status.pack()

        frame_btn = ctk.CTkFrame(popup, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=15)
        ctk.CTkButton(frame_btn, text=self.i18n.t("btn_open_settings", "Ouvrir les Réglages"), fg_color="#27ae60", hover_color="#2ecc71",
                      command=lambda: pb.open_permission_settings("accessibility")).pack(side="left", expand=True, padx=10)
        ctk.CTkButton(frame_btn, text=self.i18n.t("settings_close", "Fermer"), fg_color="#7f8c8d", hover_color="#95a5a6",
                      command=popup.destroy).pack(side="right", expand=True, padx=10)

        def poll():
            if not popup.winfo_exists():
                return
            if all(pb.check_permissions().values()):
                lbl_status.configure(text=self.i18n.t("msg_permissions_ok", "✅ Autorisation accordée !"), text_color="#2ecc71")
                self.refresh()
                popup.after(1500, popup.destroy)
                return
            popup.after(1000, poll)
        poll()

    def update_volume(self, volume_val):
        self.config.data["volume_level"] = volume_val
        self.config.save()
        vol_float = volume_val / 100.0
        self.radial_focus.set_base_volume(vol_float)

    def check_conflicting_software(self):
        if self.config.data.get("ignore_organizer_warning", False):
            return
        try:
            if pb.is_process_running("organizer.exe"):
                self.show_conflict_popup()
        except Exception: pass

    def show_conflict_popup(self):
        popup = ctk.CTkToplevel(self.gui.root)
        popup.title(self.i18n.t("popup_conflict_title", "⚠️ Conflit de logiciels détecté"))
        popup.geometry("480x250")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        popup.transient(self.gui.root)
        
        popup.update_idletasks()
        x = self.gui.root.winfo_x() + (self.gui.root.winfo_width() // 2) - (480 // 2)
        y = self.gui.root.winfo_y() + (self.gui.root.winfo_height() // 2) - (250 // 2)
        popup.geometry(f"+{x}+{y}")

        msg = self.i18n.t(
            "popup_conflict_text",
            "Le logiciel 'Organizer' est actuellement ouvert.\nL'utilisation de deux gestionnaires de pages simultanément\nva créer des bugs et des conflits de focus sur DOSOFT.\n\nNous vous recommandons fortement de le fermer."
        )
        
        lbl = ctk.CTkLabel(popup, text=msg, justify="center", font=ctk.CTkFont(size=13))
        lbl.pack(pady=(20, 15))

        var_ignore = ctk.BooleanVar(value=False)
        chk = ctk.CTkCheckBox(popup, text=self.i18n.t("popup_conflict_ignore", "Ne plus m'afficher cet avertissement"), variable=var_ignore)
        chk.pack(pady=(0, 20))

        frame_btn = ctk.CTkFrame(popup, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20)

        def on_close_organizer():
            if var_ignore.get():
                self.config.data["ignore_organizer_warning"] = True
                self.config.save()
            pb.kill_process_by_name("organizer.exe")
            popup.destroy()
            self.gui.show_temporary_message(self.i18n.t("msg_organizer_closed", "✅ Organizer fermé avec succès !"), "#2ecc71")

        def on_keep_organizer():
            if var_ignore.get():
                self.config.data["ignore_organizer_warning"] = True
                self.config.save()
            popup.destroy()

        btn_close = ctk.CTkButton(frame_btn, text=self.i18n.t("btn_close_organizer", "Fermer Organizer"), fg_color="#27ae60", hover_color="#2ecc71", command=on_close_organizer)
        btn_close.pack(side="left", expand=True, padx=10)

        btn_keep = ctk.CTkButton(frame_btn, text=self.i18n.t("btn_keep_running", "Conserver"), fg_color="#7f8c8d", hover_color="#95a5a6", command=on_keep_organizer)
        btn_keep.pack(side="right", expand=True, padx=10)
        
        popup.grab_set()

    def is_hotkey_pressed(self, hk_str):
        if not hk_str: return False
        parts = hk_str.split('+')
        for p in parts:
            token = p.lower().strip()
            if token in pb.MODIFIERS:
                if not pb.is_modifier_pressed(token):
                    return False
                continue

            if token in pb.MOUSE_BUTTONS:
                if not pb.is_mouse_pressed(token):
                    return False
                continue

            scan_code = self.keymaps.resolve_scan_code(token)
            if scan_code is not None:
                if not pb.is_pressed(scan_code):
                    return False
            elif not pb.is_pressed(token):
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
                    
                    fg_hwnd = pb.get_foreground_window()
                    current_name = None
                    for acc in active_accs:
                        if acc['hwnd'] == fg_hwnd:
                            current_name = acc['name']
                            break
                            
                    x, y = pb.get_cursor_pos()
                    self.gui.root.after(0, self.radial_focus.show, x, y, active_accs, current_name)
                    
                elif radial_was_open and not is_pressed:
                    radial_was_open = False
                    self.gui.root.after(0, self.radial_focus.hide)

            # Synchronisation de l'index au clic manuel
            try:
                fg_hwnd = pb.get_foreground_window()
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
            if p in pb.MODIFIERS:
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
        """Force le système à relâcher les touches Ctrl, Alt et Shift après la saisie."""
        pb.release_modifiers()

    def restore_modifiers(self, mods):
        pb.restore_modifiers(mods)

    def global_hook_listener(self, event):
        if event.event_type != pb.KEY_DOWN: return
        
        current_mods = set(pb.get_pressed_modifiers())
        
        key = (frozenset(current_mods), event.scan_code)
        if key in self.hotkey_actions:
            def safe_execute(mods=current_mods):
                self.release_modifiers()
                self.hotkey_actions[key]()
                time.sleep(0.05)
                self.restore_modifiers(mods)
            threading.Thread(target=safe_execute, daemon=True).start()

    def setup_hotkeys(self):
        pb.unhook_all()
        self.hotkey_actions = {} 
        self.mouse_hotkeys = {} 
        self.mouse_states = {}  
        
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
            if cfg.get('refresh_key'): self.register_action(cfg['refresh_key'], self.refresh)
            if cfg.get('quit_key'):    self.register_action(cfg['quit_key'],   self.quit_app) 
            pb.hook(self.global_hook_listener)
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
        if getattr(self, "tray_icon", None) is not None:
            try: self.tray_icon.stop()
            except Exception: pass
        pb.force_quit_self()

    def start_notification_listener(self):
        mode = self.config.data.get("notif_api_mode", "v2")
        pb.start_notification_listener(mode, self.handle_notification_texts)

    def handle_notification_texts(self, texts):
        """Auto-Focus Rétro : focus la page du personnage cité dans la notification.

        Retourne True si la notification provient de Dofus Rétro.
        """
        is_retro = self.config.data.get("game_version", "Unity") == "Rétro"
        is_autofocus_on = self.config.data.get("auto_focus_retro", False)
        if not (is_retro and is_autofocus_on):
            return False
        for ligne in texts:
            if " - Dofus Retro" in ligne:
                pseudo = ligne.split(" - ")[0].strip()
                cycle_list = self.logic.get_cycle_list()
                for index, acc in enumerate(cycle_list):
                    if acc['name'] == pseudo:
                        self.gui.root.after(0, self.logic.focus_window, acc['hwnd'])
                        self.current_idx = index
                        break
                return True
        return False

VERSION_URL = "https://raw.githubusercontent.com/LuframeCode/Dosoft/main/version.json"


def is_newer_version(candidate, current):
    """Return whether a dotted numeric candidate version is newer than current."""
    def parse(value):
        parts = str(value).split(".")
        if not parts or any(not part.isdigit() for part in parts):
            return None
        return tuple(int(part) for part in parts)

    candidate_parts = parse(candidate)
    current_parts = parse(current)
    if candidate_parts is None or current_parts is None:
        return False
    length = max(len(candidate_parts), len(current_parts))
    candidate_parts += (0,) * (length - len(candidate_parts))
    current_parts += (0,) * (length - len(current_parts))
    return candidate_parts > current_parts


def check_version(i18n=None):
    i18n = i18n or I18nManager("fr")
    try:
        response = requests.get(VERSION_URL, timeout=5)
        response.raise_for_status() 
        data = response.json()
        latest_version = data.get("version")

        if latest_version and is_newer_version(latest_version, CURRENT_VERSION):
            message = i18n.t(
                "version_update_required_text",
                "Une mise à jour est requise pour utiliser le logiciel.\n\nVotre version : {current_version}\nVersion disponible : {latest_version}\n\nMise à jour dispo sur Dosoft.fr"
            ).format(current_version=CURRENT_VERSION, latest_version=latest_version)
            pb.show_error_box(i18n.t("version_update_required_title", "Mise à jour requise"), message)
    except requests.RequestException:
        pb.show_error_box(
            i18n.t("version_network_error_title", "Erreur réseau"),
            i18n.t("version_network_error_text", "Impossible de vérifier la version.")
        )
        

def start_application():
    pb.ensure_privileges()  # Windows : relance en admin / macOS : demande Accessibilité
    cfg = Config()
    _app_mutex = pb.acquire_single_instance(I18nManager(cfg.data.get("language", "fr")), APP_TITLE)
    check_version(I18nManager(cfg.data.get("language", "fr")))

    app = OrganizerApp()
    app.gui.run()

if __name__ == "__main__":
    start_application()
