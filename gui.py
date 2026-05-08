import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import keyboard
import threading
import time
import win32api
import win32con
import os
import webbrowser
from PIL import Image, ImageTk
from i18n_manager import I18nManager
from config_manager import Config
from app_version import APP_TITLE


ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")  

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent_gui):
        super().__init__(parent_gui.root)
        self.parent = parent_gui
        self.app = parent_gui.app
        self.title(self.app.i18n.t("settings_title", "⚙️ Paramètres"))
        self.geometry("450x500")
        self.minsize(350, 300)
        self.attributes("-topmost", True)
        self.resizable(True, True)

        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True, padx=5, pady=5)

        title_font = ctk.CTkFont(size=16, weight="bold")

        self.lbl_settings_radial = ctk.CTkLabel(self.scroll_container, text=self.app.i18n.t("settings_radial", "Roue de Focus (Radiale)"), font=title_font)
        self.lbl_settings_radial.pack(pady=(20, 5))
        frame_radial = ctk.CTkFrame(self.scroll_container)
        frame_radial.pack(fill="x", padx=10, pady=5)
        
        self.var_radial = ctk.BooleanVar(value=self.app.config.data.get("radial_menu_active", True))
        self.sw_radial = ctk.CTkSwitch(frame_radial, text=self.app.i18n.t("settings_radial_enable", "Activer la roue"), variable=self.var_radial, command=self.save_settings)
        self.sw_radial.pack(pady=10)

        frame_hk = ctk.CTkFrame(frame_radial, fg_color="transparent")
        frame_hk.pack(pady=(0, 10))
        
        self.lbl_hk = ctk.CTkLabel(frame_hk, text=self.app.i18n.t("settings_hotkey", "Raccourci :"))
        self.lbl_hk.pack(side="left", padx=5)
        
        current_val = self.app.config.data.get("radial_menu_hotkey", "alt+left_click")
        btn_hk = ctk.CTkButton(frame_hk, text=current_val if current_val else self.app.i18n.t("none", "Aucun"), width=120, command=lambda: self.parent.catch_key("radial_menu_hotkey", btn_hk, allow_mouse=True))
        btn_hk.pack(side="left", padx=5)
        
        self.parent.hotkey_btns["radial_menu_hotkey"] = btn_hk

        btn_x = ctk.CTkButton(frame_hk, text="✖", width=25, fg_color="#c0392b", hover_color="#e74c3c", command=lambda: self.parent.clear_key("radial_menu_hotkey", btn_hk))
        btn_x.pack(side="left", padx=5)

        frame_language = ctk.CTkFrame(self.scroll_container)
        frame_language.pack(fill="x", padx=10, pady=5)
        self.lbl_language = ctk.CTkLabel(frame_language, text=self.app.i18n.t("settings_language", "Langue"))
        self.lbl_language.pack(side="left", padx=8, pady=8)
        self.var_language = ctk.StringVar(value=self.app.config.data.get("language", "fr"))
        ctk.CTkOptionMenu(frame_language, values=["fr", "en", "pt"], variable=self.var_language, command=lambda _: self.save_settings()).pack(side="right", padx=8, pady=8)

        frame_keyboard = ctk.CTkFrame(self.scroll_container)
        frame_keyboard.pack(fill="x", padx=10, pady=5)
        self.lbl_keyboard = ctk.CTkLabel(frame_keyboard, text=self.app.i18n.t("settings_keyboard_layout", "Disposition clavier"))
        self.lbl_keyboard.pack(side="left", padx=8, pady=8)
        self.var_keyboard_layout = ctk.StringVar(value=self.app.config.data.get("keyboard_layout", "azerty_fr"))
        ctk.CTkOptionMenu(frame_keyboard, values=["azerty_fr", "qwerty_us"], variable=self.var_keyboard_layout, command=lambda _: self.save_settings()).pack(side="right", padx=8, pady=8)
        
        # --- Overlay bar ---
        frame_overlay = ctk.CTkFrame(self.scroll_container)
        frame_overlay.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(frame_overlay, text=self.app.i18n.t("settings_overlay", "Barre overlay")).pack(side="left", padx=8, pady=8)
        self.var_overlay = ctk.BooleanVar(value=self.app.config.data.get("overlay_enabled", True))
        ctk.CTkSwitch(frame_overlay, text="", variable=self.var_overlay, command=self._save_overlay).pack(side="right", padx=8)

        # --- Teams ---
        lbl_teams = ctk.CTkLabel(self.scroll_container, text=self.app.i18n.t("settings_teams", "Équipes"), font=title_font)
        lbl_teams.pack(pady=(15, 5))

        frame_team_count = ctk.CTkFrame(self.scroll_container)
        frame_team_count.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(frame_team_count, text=self.app.i18n.t("settings_team_count", "Nombre d'équipes")).pack(side="left", padx=8, pady=8)
        self.var_team_count = ctk.IntVar(value=self.app.config.data.get("team_count", 2))
        ctk.CTkOptionMenu(frame_team_count, values=["2", "3", "4"],
                          variable=ctk.StringVar(value=str(self.var_team_count.get())),
                          command=self._on_team_count_change).pack(side="right", padx=8, pady=8)

        frame_team_names = ctk.CTkFrame(self.scroll_container)
        frame_team_names.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(frame_team_names, text=self.app.i18n.t("settings_team_names", "Noms d'équipes")).pack(padx=8, pady=(8, 2))
        self._team_name_entries = {}
        team_names_cfg = self.app.config.data.get("team_names", {})
        team_count = self.app.config.data.get("team_count", 2)
        for i in range(1, team_count + 1):
            key = f"Team {i}"
            row = ctk.CTkFrame(frame_team_names, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(row, text=f"T{i}:", width=30).pack(side="left")
            ent = ctk.CTkEntry(row, width=140)
            ent.insert(0, team_names_cfg.get(key, key))
            ent.pack(side="left", padx=4)
            ent.bind("<FocusOut>", lambda e, k=key, en=ent: self._save_team_name(k, en))
            ent.bind("<Return>", lambda e, k=key, en=ent: self._save_team_name(k, en))
            self._team_name_entries[key] = ent

        # --- Layout Manager ---
        lbl_layout = ctk.CTkLabel(self.scroll_container, text=self.app.i18n.t("settings_layout", "Disposition des fenêtres"), font=title_font)
        lbl_layout.pack(pady=(15, 5))

        frame_layout = ctk.CTkFrame(self.scroll_container)
        frame_layout.pack(fill="x", padx=10, pady=5)

        frame_layout_btns = ctk.CTkFrame(frame_layout, fg_color="transparent")
        frame_layout_btns.pack(fill="x", padx=8, pady=5)
        ctk.CTkButton(frame_layout_btns, text=self.app.i18n.t("btn_save_layout", "Sauvegarder"), width=120,
                      command=self._save_layout).pack(side="left", padx=4)
        ctk.CTkButton(frame_layout_btns, text=self.app.i18n.t("btn_restore_layout", "Restaurer"), width=120,
                      command=self._restore_layout).pack(side="left", padx=4)

        frame_grid = ctk.CTkFrame(frame_layout, fg_color="transparent")
        frame_grid.pack(fill="x", padx=8, pady=(0, 5))
        ctk.CTkLabel(frame_grid, text=self.app.i18n.t("label_grid_preset", "Grille:")).pack(side="left", padx=4)
        for grid_name in ["2x2", "1+3", "3+1"]:
            ctk.CTkButton(frame_grid, text=grid_name, width=55, height=26,
                          fg_color="#34495e", hover_color="#2c3e50",
                          command=lambda g=grid_name: self._apply_grid(g)).pack(side="left", padx=2)

        # --- Export / Import ---
        lbl_export = ctk.CTkLabel(self.scroll_container, text=self.app.i18n.t("settings_export", "Sauvegarde Configuration"), font=title_font)
        lbl_export.pack(pady=(15, 5))

        frame_export = ctk.CTkFrame(self.scroll_container)
        frame_export.pack(fill="x", padx=10, pady=5)
        frame_export_btns = ctk.CTkFrame(frame_export, fg_color="transparent")
        frame_export_btns.pack(pady=8)
        ctk.CTkButton(frame_export_btns, text=self.app.i18n.t("btn_export", "📤 Exporter"), width=120,
                      command=self._export_config).pack(side="left", padx=8)
        ctk.CTkButton(frame_export_btns, text=self.app.i18n.t("btn_import", "📥 Importer"), width=120,
                      fg_color="#27ae60", hover_color="#2ecc71",
                      command=self._import_config).pack(side="left", padx=8)

        self.btn_close = ctk.CTkButton(self.scroll_container, text=self.app.i18n.t("settings_close", "Fermer"), fg_color="#7f8c8d", command=self.destroy)
        self.btn_close.pack(pady=(20, 10))

    def _save_overlay(self):
        self.app.config.data["overlay_enabled"] = self.var_overlay.get()
        self.app.config.save()

    def _on_team_count_change(self, val):
        self.app.config.data["team_count"] = int(val)
        self.app.config.save()
        # Rebuild the main mode combo
        team_count = int(val)
        team_values = ["ALL"] + [f"Team {i+1}" for i in range(team_count)]
        self.parent.combo_mode.configure(values=team_values)

    def _save_team_name(self, key, entry_widget):
        val = entry_widget.get().strip() or key
        self.app.config.data.setdefault("team_names", {})[key] = val
        self.app.config.save()

    def _save_layout(self):
        import tkinter.simpledialog as sd
        name = sd.askstring(
            self.app.i18n.t("dialog_layout_name_title", "Nom de la disposition"),
            self.app.i18n.t("dialog_layout_name_prompt", "Entrez un nom pour cette disposition :"),
            parent=self,
        )
        if name:
            self.app.logic.save_layout(name.strip())
            self.parent.show_temporary_message(
                self.app.i18n.t("msg_layout_saved", "✅ Disposition '{n}' sauvegardée !").format(n=name), "#2ecc71"
            )

    def _restore_layout(self):
        presets = self.app.config.data.get("layout_presets", {})
        if not presets:
            messagebox.showinfo(
                self.app.i18n.t("dialog_no_layout_title", "Aucune disposition"),
                self.app.i18n.t("dialog_no_layout_text", "Aucune disposition sauvegardée."),
                parent=self,
            )
            return
        import tkinter.simpledialog as sd
        names = list(presets.keys())
        name = sd.askstring(
            self.app.i18n.t("dialog_restore_layout_title", "Restaurer disposition"),
            self.app.i18n.t("dialog_restore_layout_prompt", "Dispositions disponibles: {list}\n\nNom à restaurer:").format(list=", ".join(names)),
            parent=self,
        )
        if name and name.strip() in presets:
            ok = self.app.logic.restore_layout(name.strip())
            if ok:
                self.parent.show_temporary_message(
                    self.app.i18n.t("msg_layout_restored", "✅ Disposition '{n}' restaurée !").format(n=name), "#2ecc71"
                )

    def _apply_grid(self, grid_name):
        self.app.logic.apply_grid_layout(grid_name)
        self.parent.show_temporary_message(
            self.app.i18n.t("msg_grid_applied", "✅ Grille {g} appliquée !").format(g=grid_name), "#2ecc71"
        )

    def _export_config(self):
        import json
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="dosoft_config.json",
            title=self.app.i18n.t("dialog_export_title", "Exporter la configuration"),
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    import json
                    json.dump(self.app.config.data, f, indent=4, ensure_ascii=False)
                self.parent.show_temporary_message(
                    self.app.i18n.t("msg_export_ok", "✅ Configuration exportée !"), "#2ecc71"
                )
            except Exception as e:
                messagebox.showerror("Export", str(e), parent=self)

    def _import_config(self):
        import json
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[("JSON", "*.json")],
            title=self.app.i18n.t("dialog_import_title", "Importer la configuration"),
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.app.config.data.update(loaded)
                self.app.config.save()
                self.app.setup_hotkeys()
                self.app.refresh()
                self.parent.show_temporary_message(
                    self.app.i18n.t("msg_import_ok", "✅ Configuration importée !"), "#2ecc71"
                )
            except Exception as e:
                messagebox.showerror("Import", str(e), parent=self)

    def save_settings(self):
        previous_language = self.app.config.data.get("language", "fr")
        self.app.config.data["radial_menu_active"] = self.var_radial.get()
        self.app.config.data["language"] = self.var_language.get()
        self.app.config.data["keyboard_layout"] = self.var_keyboard_layout.get()
        self.app.i18n.set_locale(self.var_language.get())
        self.app.keymaps.set_layout(self.var_keyboard_layout.get())
        self.app.setup_hotkeys()
        self.app.config.save()
        self.parent.apply_translations()
        self.apply_translations()

        if previous_language != self.var_language.get():
            self.title(self.app.i18n.t("settings_title", "⚙️ Paramètres"))

    def apply_translations(self):
        self.title(self.app.i18n.t("settings_title", "⚙️ Paramètres"))
        self.lbl_settings_radial.configure(text=self.app.i18n.t("settings_radial", "Roue de Focus (Radiale)"))
        self.sw_radial.configure(text=self.app.i18n.t("settings_radial_enable", "Activer la roue"))
        self.lbl_hk.configure(text=self.app.i18n.t("settings_hotkey", "Raccourci :"))
        self.lbl_language.configure(text=self.app.i18n.t("settings_language", "Langue"))
        self.lbl_keyboard.configure(text=self.app.i18n.t("settings_keyboard_layout", "Disposition clavier"))
        self.btn_close.configure(text=self.app.i18n.t("settings_close", "Fermer"))


class OrganizerGUI:
    
    def __init__(self, app_controller):
        self.app = app_controller
        self.root = ctk.CTk()
        self.root.title(APP_TITLE)
        
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = 700
        win_h = min(screen_h - 80, 850) 
        x_pos = int((screen_w / 2) - (win_w / 2))
        y_pos = int((screen_h / 2) - (win_h / 2))
        self.root.geometry(f"{win_w}x{win_h}+{x_pos}+{y_pos}") 
        
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.original_app_refresh = self.app.refresh

        

        if os.path.exists("logo.ico"):
            try: self.root.iconbitmap("logo.ico")
            except: pass
                
        self.is_listening = False
        self.is_visible = True 
        cfg = self.app.config.data 
        
        self.var_tooltips = ctk.BooleanVar(value=cfg.get("show_tooltips", True))
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.overrideredirect(True)
        self.tooltip.attributes("-topmost", True)
        self.tooltip_lbl = tk.Label(self.tooltip, text="", fg="#ecf0f1", bg="#2c3e50", font=("Segoe UI", 9), padx=6, pady=3, relief="solid", borderwidth=1)
        self.tooltip_lbl.pack()
        self.tooltip.withdraw() 
        
        self.hotkey_btns = {}
        self.hotkey_labels = {}
        self.tooltip_i18n_map = {}

        self.header_f = ctk.CTkFrame(self.root, fg_color="transparent")
        self.header_f.pack(fill="x", padx=15, pady=(15, 5))
        
        self.lbl_app_title = ctk.CTkLabel(self.header_f, text=APP_TITLE, font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_app_title.pack(side="left")
        
        self.btn_settings = ctk.CTkButton(self.header_f, text=self.app.i18n.t("header_settings", "⚙️ Paramètres"), fg_color="#34495e", hover_color="#2c3e50", width=120, command=self.open_settings)
        self.btn_settings.pack(side="right")
        self.bind_i18n_tooltip(self.btn_settings, "tooltip_settings", "Paramétrer la roue radiale")

        self.btn_tuto = ctk.CTkButton(self.header_f, text=self.app.i18n.t("header_tutorial", "🎓 Tuto"), fg_color="#8e44ad", hover_color="#9b59b6", width=80, command=self.launch_tutorial)
        self.btn_tuto.pack(side="right", padx=(0, 10))

        # --- NOUVEAU BOUTON OFF ---
        self.btn_off = ctk.CTkButton(self.header_f, text=self.app.i18n.t("header_off", "🔴 OFF"), fg_color="#c0392b", hover_color="#e74c3c", width=60, command=self.app.quit_app)
        self.btn_off.pack(side="right", padx=(0, 10))
        self.bind_i18n_tooltip(self.btn_off, "tooltip_off", "Fermer complètement DOSOFT")
        # --------------------------

        self.frame_mode = ctk.CTkFrame(self.root)
        self.frame_mode.pack(fill="x", padx=15, pady=5)
        
        self.lbl_controls = ctk.CTkLabel(self.frame_mode, text=self.app.i18n.t("label_controls", "Contrôler :"))
        self.lbl_controls.pack(side="left", padx=10, pady=5)
        
        team_count = cfg.get("team_count", 2)
        team_values = ["ALL"] + [f"Team {i+1}" for i in range(team_count)]
        self.combo_mode = ctk.CTkOptionMenu(self.frame_mode, values=team_values, command=self.on_mode_change)
        self.combo_mode.set(cfg.get("current_mode", "ALL"))
        self.combo_mode.pack(side="left", padx=5, pady=5)

        self.lbl_versions = ctk.CTkLabel(self.frame_mode, text=self.app.i18n.t("label_versions", "Versions :"))
        self.lbl_versions.pack(side="left", padx=(20, 5), pady=5)
        
        self.combo_version = ctk.CTkOptionMenu(self.frame_mode, values=["Unity", "Rétro"], width=100, fg_color="#8e44ad", button_color="#9b59b6", button_hover_color="#8e44ad", command=self.on_version_change)
        self.combo_version.set(cfg.get("game_version", "Unity"))
        self.combo_version.pack(side="left", padx=5, pady=5)

        self.var_autofocus = ctk.BooleanVar(value=cfg.get("auto_focus_retro", False))
        self.chk_autofocus = ctk.CTkCheckBox(self.frame_mode, text=self.app.i18n.t("label_auto_focus", "Auto-Focus 🔔"), variable=self.var_autofocus, command=self.toggle_autofocus, width=110)
        
        if cfg.get("game_version", "Unity") == "Rétro":
            self.chk_autofocus.pack(side="left", padx=(15, 5))
            
        self.bind_i18n_tooltip(self.chk_autofocus, "tooltip_auto_focus", "Focus automatiquement la page Rétro lors d'une notification")

        self.frame_keys = ctk.CTkFrame(self.root)
        self.frame_keys.pack(fill="x", padx=15, pady=10)
        self.lbl_keyboard_shortcuts = ctk.CTkLabel(self.frame_keys, text=self.app.i18n.t("label_keyboard_shortcuts", "Raccourcis Clavier"), font=ctk.CTkFont(weight="bold"))
        self.lbl_keyboard_shortcuts.grid(row=0, column=0, columnspan=6, pady=5)

        self.create_hotkey_row(self.frame_keys, "hotkey_prev", "prev_key", 1, 0, "tooltip_prev")
        self.create_hotkey_row(self.frame_keys, "hotkey_next", "next_key", 1, 3, "tooltip_next")
        self.create_hotkey_row(self.frame_keys, "hotkey_leader", "leader_key", 2, 0, "tooltip_leader")
        self.create_hotkey_row(self.frame_keys, "hotkey_toggle_ui", "toggle_app_key", 2, 3, "tooltip_toggle_ui")
        self.create_hotkey_row(self.frame_keys, "hotkey_refresh", "refresh_key", 1, 6, "tooltip_refresh")
        self.create_hotkey_row(self.frame_keys, "hotkey_quit", "quit_key", 2, 6, "tooltip_quit")
        self.create_hotkey_row(self.frame_keys, "hotkey_back", "back_key", 3, 0, "tooltip_back")

        # --- Broadcast mode row ---
        frame_broadcast = ctk.CTkFrame(self.root)
        frame_broadcast.pack(fill="x", padx=15, pady=(0, 5))

        lbl_bc = ctk.CTkLabel(frame_broadcast, text=self.app.i18n.t("label_broadcast", "📡 Broadcast :"),
                              font=ctk.CTkFont(weight="bold"))
        lbl_bc.pack(side="left", padx=10, pady=5)

        self.var_broadcast = ctk.BooleanVar(value=self.app.config.data.get("broadcast_mode", False))
        self.sw_broadcast = ctk.CTkSwitch(
            frame_broadcast, text="", variable=self.var_broadcast,
            onvalue=True, offvalue=False,
            progress_color="#e67e22",
            command=self._on_broadcast_toggle,
        )
        self.sw_broadcast.pack(side="left", padx=5)

        self.lbl_bc_warn = ctk.CTkLabel(
            frame_broadcast,
            text=self.app.i18n.t("label_broadcast_warn", "⚠️ Risque CGU — désactivé par défaut"),
            font=ctk.CTkFont(size=10),
            text_color="#e67e22",
        )
        self.lbl_bc_warn.pack(side="left", padx=5)

        # Broadcast VK key picker (shows when enabled)
        self.frame_bc_key = ctk.CTkFrame(frame_broadcast, fg_color="transparent")
        self.frame_bc_key.pack(side="left", padx=10)
        ctk.CTkLabel(self.frame_bc_key, text=self.app.i18n.t("label_broadcast_key", "Touche:"), font=ctk.CTkFont(size=11)).pack(side="left")
        bc_key_val = self.app.config.data.get("broadcast_key", "")
        self.btn_bc_key = ctk.CTkButton(
            self.frame_bc_key,
            text=bc_key_val if bc_key_val else self.app.i18n.t("none", "Aucun"),
            width=80,
            command=lambda: self.catch_key("broadcast_key", self.btn_bc_key, allow_mouse=False),
        )
        self.btn_bc_key.pack(side="left", padx=4)
        self.hotkey_btns["broadcast_key"] = self.btn_bc_key
        if not self.var_broadcast.get():
            self.frame_bc_key.pack_forget()

        self.frame_actions = ctk.CTkFrame(self.root)
        self.frame_actions.pack(fill="x", padx=15, pady=5)

        self.lbl_volume = ctk.CTkLabel(self.frame_actions, text=self.app.i18n.t("label_volume", "🔊 Volume :"))
        self.lbl_volume.pack(side="left", padx=10)
        self.slider_volume = ctk.CTkSlider(self.frame_actions, from_=0, to=100, command=self.on_volume_change, width=150)
        self.slider_volume.set(cfg.get("volume_level", 50))
        self.slider_volume.pack(side="left", padx=10, pady=10)
        
        self.btn_close_all = ctk.CTkButton(self.frame_actions, text=self.app.i18n.t("btn_close_team", "Fermer Team"), fg_color="#c0392b", hover_color="#e74c3c", command=self.close_all_and_refresh, width=120)
        self.btn_close_all.pack(side="right", padx=10)

        self.btn_restore_all = ctk.CTkButton(self.frame_actions, text=self.app.i18n.t("btn_restore_all", "▲ Restaurer"), fg_color="#27ae60", hover_color="#2ecc71", command=lambda: self.app.logic.restore_all(), width=100)
        self.btn_restore_all.pack(side="right", padx=5)

        self.btn_minimize_all = ctk.CTkButton(self.frame_actions, text=self.app.i18n.t("btn_minimize_all", "▼ Minimiser"), fg_color="#34495e", hover_color="#2c3e50", command=lambda: self.app.logic.minimize_all(), width=100)
        self.btn_minimize_all.pack(side="right", padx=5)

        self.btn_reset = ctk.CTkButton(self.frame_actions, text=self.app.i18n.t("btn_reset_settings", "Reset Settings"), fg_color="#7f8c8d", hover_color="#95a5a6", command=self.reset_all, width=120)
        self.btn_reset.pack(side="right", padx=10)

        # --- NOUVEAU DESIGN : Barre Comptes Actifs avec Binds Avancés ---
        pill_frame = ctk.CTkFrame(self.root, fg_color="#3b4252", corner_radius=8)
        pill_frame.pack(fill="x", padx=15, pady=(10, 0), ipadx=5, ipady=2)

        self.lbl_accounts = ctk.CTkLabel(pill_frame, text=self.app.i18n.t("label_active_accounts", "Comptes actifs"), font=ctk.CTkFont(size=13, weight="normal"), text_color="#ecf0f1")
        self.lbl_accounts.pack(side="left", padx=10, pady=4)

        btn_manage_binds = ctk.CTkButton(pill_frame, text="⚙️", width=28, height=28, 
                                        fg_color="#2c3e50", hover_color="#1a252f", corner_radius=6,
                                        command=self.open_bind_manager)
        btn_manage_binds.pack(side="right", padx=5, pady=4)
        self.bind_i18n_tooltip(btn_manage_binds, "tooltip_manage_binds", "Gérer les raccourcis avancés par personnage")

        self.scroll_frame = ctk.CTkScrollableFrame(self.root)
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=(5, 10))
        
        # --- CORRECTION PIED DE PAGE ---
        self.frame_footer = ctk.CTkFrame(self.root, fg_color="transparent")
        self.frame_footer.pack(side="bottom", fill="x", padx=15, pady=(0, 15))
        
        self.btn_refresh = ctk.CTkButton(self.frame_footer, text=self.app.i18n.t("btn_refresh", "Rafraîchir"), command=self.original_app_refresh, width=80)
        self.btn_refresh.pack(side="left")

        self.btn_sort_win = ctk.CTkButton(self.frame_footer, text=self.app.i18n.t("btn_sort_taskbar", "Trier Barre Windows"), fg_color="#8e44ad", hover_color="#9b59b6", command=self.trigger_sort_taskbar, width=120)
        self.btn_sort_win.pack(side="left", padx=5)
        
        self.chk_tooltips = ctk.CTkCheckBox(self.frame_footer, text=self.app.i18n.t("label_tooltips", "Bulles"), variable=self.var_tooltips, command=self.toggle_tooltips_setting, width=60)
        self.chk_tooltips.pack(side="left", padx=15)
        
        self.btn_hide = ctk.CTkButton(self.frame_footer, text=self.app.i18n.t("btn_hide_ui", "Cacher l'UI"), command=self.toggle_visibility, fg_color="transparent", border_width=1, width=70)
        self.btn_hide.pack(side="right")

        frame_msg = ctk.CTkFrame(self.root, fg_color="transparent", height=20)
        frame_msg.pack(fill="x", padx=15, pady=(0, 5))
        self.lbl_feedback = ctk.CTkLabel(frame_msg, text="", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_feedback.pack(expand=True)
        
        self.skin_cache = {} 

    def apply_translations(self):
        none_label = self.app.i18n.t("none", "Aucun")
        self.root.title(APP_TITLE)
        self.lbl_app_title.configure(text=APP_TITLE)
        self.btn_settings.configure(text=self.app.i18n.t("header_settings", "⚙️ Paramètres"))
        self.btn_tuto.configure(text=self.app.i18n.t("header_tutorial", "🎓 Tuto"))
        self.btn_off.configure(text=self.app.i18n.t("header_off", "🔴 OFF"))
        self.lbl_controls.configure(text=self.app.i18n.t("label_controls", "Contrôler :"))
        self.lbl_versions.configure(text=self.app.i18n.t("label_versions", "Versions :"))
        self.lbl_keyboard_shortcuts.configure(text=self.app.i18n.t("label_keyboard_shortcuts", "Raccourcis Clavier"))
        self.lbl_volume.configure(text=self.app.i18n.t("label_volume", "🔊 Volume :"))
        self.btn_close_all.configure(text=self.app.i18n.t("btn_close_team", "Fermer Team"))
        self.btn_reset.configure(text=self.app.i18n.t("btn_reset_settings", "Reset Settings"))
        self.lbl_accounts.configure(text=self.app.i18n.t("label_active_accounts", "Comptes actifs"))
        self.btn_refresh.configure(text=self.app.i18n.t("btn_refresh", "Rafraîchir"))
        self.btn_sort_win.configure(text=self.app.i18n.t("btn_sort_taskbar", "Trier Barre Windows"))
        self.chk_tooltips.configure(text=self.app.i18n.t("label_tooltips", "Bulles"))
        self.btn_hide.configure(text=self.app.i18n.t("btn_hide_ui", "Cacher l'UI"))
        self.chk_autofocus.configure(text=self.app.i18n.t("label_auto_focus", "Auto-Focus 🔔"))
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.apply_translations()
        for config_key, (label_widget, label_key) in self.hotkey_labels.items():
            label_widget.configure(text=f"{self.app.i18n.t(label_key, label_key)}:")
        for widget, (tooltip_key, default_text) in self.tooltip_i18n_map.items():
            self.bind_tooltip(widget, self.app.i18n.t(tooltip_key, default_text))
        for button in self.hotkey_btns.values():
            if button.cget("text") in {"Aucun", "None", "Nenhum"}:
                button.configure(text=none_label)

    def open_settings(self):
        if not hasattr(self, 'settings_window') or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self)
        else:
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_force()

    def launch_tutorial(self):
        
        if not self.app.config.data.get("tutorial_done", False):
            self.app.config.data["tutorial_done"] = True
            self.app.config.save()

        rep = messagebox.askyesno(self.app.i18n.t("dialog_tutorial_title", "Tutoriel Vidéo"),self.app.i18n.t("dialog_tutorial_text", "Voulez-vous ouvrir la vidéo de présentation sur YouTube dans votre navigateur web ?"),self.app.i18n.t("button_yes", "Oui"),self.app.i18n.t("button_no", "Non"))
        if rep:
            webbrowser.open("")

    def toggle_from_tray(self, icon, item):
        """ Demande à l'interface de s'afficher ou de se cacher proprement """
        self.gui.root.after(0, self.gui.toggle_visibility)

    def show_temporary_message(self, text, color="#2ecc71"):
        self.lbl_feedback.configure(text=text, text_color=color)
        if hasattr(self, "feedback_timer"):
            self.root.after_cancel(self.feedback_timer)
        self.feedback_timer = self.root.after(2500, lambda: self.lbl_feedback.configure(text=""))

    def change_position(self, name, new_val_str):
        new_index = int(new_val_str) - 1
        self.app.logic.set_account_position(name, new_index)
        self.original_app_refresh()

    def move_row(self, name, direction):
        self.app.logic.move_account(name, direction)
        self.original_app_refresh()

    def trigger_sort_taskbar(self):
        self.app.logic.sort_taskbar()
        self.show_temporary_message(self.app.i18n.t("msg_sorted", "🚀 Les pages ont été rangées avec succès !"), "#9b59b6")

    def close_and_refresh(self, name):
        if not messagebox.askyesno(
            self.app.i18n.t("dialog_confirm_title", "Confirmation"),
            self.app.i18n.t("dialog_close_account", "Fermer le compte {name} ?").format(name=name),
        ):
            return
        self.app.logic.close_account_window(name)
        time.sleep(0.5)
        self.original_app_refresh()

    def close_all_and_refresh(self):
        if not messagebox.askyesno(
            self.app.i18n.t("dialog_confirm_title", "Confirmation"),
            self.app.i18n.t("dialog_close_team", "Fermer tous les comptes actifs ?"),
        ):
            return
        self.app.logic.close_all_active_accounts()
        time.sleep(0.5)
        self.original_app_refresh()
        self.show_temporary_message(self.app.i18n.t("msg_team_closed", "💥 La team a été fermée !"), "#e74c3c")

    def toggle_tooltips_setting(self):
        self.app.config.data["show_tooltips"] = self.var_tooltips.get()
        self.app.config.save()
        if not self.var_tooltips.get():
            self.tooltip.withdraw()

    def bind_tooltip(self, widget, text):
        widget.unbind("<Enter>")
        widget.unbind("<Leave>")
        widget.unbind("<Motion>")

        def on_enter(event):
            if self.is_listening or not self.app.config.data.get("show_tooltips", True): return 
            self.tooltip_lbl.config(text=text)
            self.tooltip.deiconify()
            x, y = win32api.GetCursorPos()
            self.tooltip.geometry(f"+{x + 15}+{y + 15}")
        def on_leave(event):
            if not self.is_listening: self.tooltip.withdraw()
        def on_motion(event):
            if self.is_listening or not self.app.config.data.get("show_tooltips", True): return
            x, y = win32api.GetCursorPos()
            self.tooltip.geometry(f"+{x + 15}+{y + 15}")

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        widget.bind("<Motion>", on_motion)

    def bind_i18n_tooltip(self, widget, key, default_text):
        self.tooltip_i18n_map[widget] = (key, default_text)
        self.bind_tooltip(widget, self.app.i18n.t(key, default_text))

    _TEAM_COLORS = ["#2980b9", "#c0392b", "#27ae60", "#8e44ad"]

    def _team_display(self, team_key):
        names = self.app.config.data.get("team_names", {})
        label = names.get(team_key, team_key)
        idx = int(team_key.split()[-1]) - 1 if team_key.startswith("Team ") else 0
        short = f"T{idx + 1}"
        color = self._TEAM_COLORS[idx % len(self._TEAM_COLORS)]
        return short, label, color

    def toggle_team_ui(self, name, btn):
        team_count = self.app.config.data.get("team_count", 2)
        current_team = self.app.config.data.get("accounts_team", {}).get(name, "Team 1")
        try:
            current_n = int(current_team.split()[-1])
        except (ValueError, IndexError):
            current_n = 1
        next_n = (current_n % team_count) + 1
        new_team = f"Team {next_n}"
        self.app.logic.change_team(name, new_team)
        short, _, color = self._team_display(new_team)
        btn.configure(text=short, fg_color=color)

    def _afk_text(self, name):
        ts = self.app.last_focused.get(name)
        if ts is None:
            return ""
        elapsed = int((time.time() - ts) / 60)
        if elapsed < 1:
            return "< 1m"
        return f"{elapsed}m"

    def refresh_list(self, accounts):
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        leader_name = self.app.config.data.get("leader_name", "")

        is_retro = self.app.config.data.get("game_version", "Unity") == "Rétro"
        retro_classes = ["Inconnu", "Feca", "Osamodas", "Enutrof", "Sram", "Xelor", "Ecaflip", "Eniripsa", "Iop", "Cra", "Sadida", "Sacrieur", "Pandawa"]

        for idx, acc in enumerate(accounts):
            name = acc['name']
            row_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            img = self.get_class_image(acc.get('classe', 'Inconnu'), is_retro)
            if img: ctk.CTkLabel(row_frame, image=img, text="").pack(side="left", padx=5)
            else: ctk.CTkLabel(row_frame, text="👤").pack(side="left", padx=5)

            var = tk.BooleanVar(value=acc['active'])

            # Name + optional sublabel in a small column
            name_col = ctk.CTkFrame(row_frame, fg_color="transparent")
            name_col.pack(side="left", padx=(5, 0))

            chk_width = 110 if is_retro else 150
            chk = ctk.CTkCheckBox(name_col, text=name[:15], variable=var, width=chk_width,
                                  command=lambda n=name, v=var: self.app.logic.toggle_account(n, v.get()))
            chk.pack(anchor="w")

            # Custom label subtitle (click to edit)
            user_label = self.app.config.data.get("account_labels", {}).get(name, "")
            lbl_sub = ctk.CTkLabel(name_col, text=user_label if user_label else "", font=ctk.CTkFont(size=9),
                                   text_color="#95a5a6", width=chk_width, anchor="w")
            lbl_sub.pack(anchor="w")
            lbl_sub.bind("<Button-1>", lambda e, n=name, l=lbl_sub: self._edit_account_label(n, l))

            # AFK timer label (right side of name col)
            afk_lbl = ctk.CTkLabel(name_col, text=self._afk_text(name),
                                   font=ctk.CTkFont(size=9), text_color="#7f8c8d", width=30, anchor="e")
            afk_lbl.pack(anchor="e")
            self._schedule_afk_refresh(afk_lbl, name)

            if is_retro:
                combo_classe = ctk.CTkOptionMenu(
                    row_frame,
                    values=retro_classes,
                    width=90, height=24,
                    fg_color="#34495e", button_color="#2c3e50", button_hover_color="#1a252f",
                    command=lambda val, n=name: self.change_retro_class(n, val)
                )
                combo_classe.set(acc.get('classe', 'Inconnu'))
                combo_classe.pack(side="left", padx=5)

            btn_close = ctk.CTkButton(row_frame, text="✖", width=25, fg_color="#c0392b", hover_color="#e74c3c")
            btn_close.configure(command=lambda n=name: self.close_and_refresh(n))
            btn_close.pack(side="right", padx=(2, 5))
            self.bind_i18n_tooltip(btn_close, "tooltip_close_game", "Fermer instantanément le jeu")

            is_leader = (name == leader_name)
            leader_txt = "🌟" if is_leader else "☆"
            leader_color = "#f39c12" if is_leader else "transparent"
            btn_lead = ctk.CTkButton(row_frame, text=leader_txt, width=35, fg_color=leader_color, border_width=1,
                                     command=lambda n=name: self.set_leader(n))
            btn_lead.pack(side="right", padx=2)
            self.bind_i18n_tooltip(btn_lead, "tooltip_set_leader", "Définir comme Chef")

            team_val = acc.get('team', "Team 1")
            short, _, color = self._team_display(team_val)
            btn_team = ctk.CTkButton(row_frame, text=short, width=35, fg_color=color)
            btn_team.configure(command=lambda n=name, b=btn_team: self.toggle_team_ui(n, b))
            btn_team.pack(side="right", padx=5)
            self.bind_i18n_tooltip(btn_team, "tooltip_change_team", "Changer d'équipe")

            btn_down = ctk.CTkButton(row_frame, text="▼", width=25, fg_color="#34495e", hover_color="#2c3e50")
            btn_down.configure(command=lambda n=name: self.move_row(n, 1))
            btn_down.pack(side="right", padx=(2, 10))
            self.bind_i18n_tooltip(btn_down, "tooltip_move_down", "Descendre dans l'initiative")

            btn_up = ctk.CTkButton(row_frame, text="▲", width=25, fg_color="#34495e", hover_color="#2c3e50")
            btn_up.configure(command=lambda n=name: self.move_row(n, -1))
            btn_up.pack(side="right", padx=2)
            self.bind_i18n_tooltip(btn_up, "tooltip_move_up", "Monter dans l'initiative")

            pos_values = [str(i+1) for i in range(len(accounts))]
            current_pos = str(idx + 1)
            combo_pos = ctk.CTkOptionMenu(row_frame, values=pos_values, width=50, height=24,
                                          fg_color="#34495e", button_color="#2c3e50", button_hover_color="#1a252f")
            combo_pos.set(current_pos)
            combo_pos.configure(command=lambda val, n=name: self.change_position(n, val))
            combo_pos.pack(side="right", padx=(2, 5))
            self.bind_i18n_tooltip(combo_pos, "tooltip_exact_position", "Choisir la position exacte")

    def _schedule_afk_refresh(self, label_widget, name):
        def _update():
            try:
                if label_widget.winfo_exists():
                    label_widget.configure(text=self._afk_text(name))
                    self.root.after(60000, _update)
            except Exception:
                pass
        self.root.after(60000, _update)

    def _edit_account_label(self, name, lbl_widget):
        current = self.app.config.data.get("account_labels", {}).get(name, "")
        entry = ctk.CTkEntry(lbl_widget.master, width=120, height=18, font=ctk.CTkFont(size=9))
        entry.insert(0, current)
        entry.place(in_=lbl_widget, relx=0, rely=0, anchor="nw")
        entry.focus_set()

        def save(event=None):
            val = entry.get().strip()
            self.app.config.data.setdefault("account_labels", {})[name] = val
            self.app.config.save()
            lbl_widget.configure(text=val)
            entry.destroy()

        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)

    def _on_broadcast_toggle(self):
        enabled = self.var_broadcast.get()
        self.app.config.data["broadcast_mode"] = enabled
        self.app.config.save()
        self.app.setup_hotkeys()
        if enabled:
            self.frame_bc_key.pack(side="left", padx=10)
        else:
            self.frame_bc_key.pack_forget()

    def toggle_autofocus(self):
        self.app.config.data["auto_focus_retro"] = self.var_autofocus.get()
        self.app.config.save()
        
    def on_volume_change(self, value): self.app.update_volume(int(value))
    
    def create_hotkey_row(self, parent, label_key, config_key, row, col_offset, tooltip_key=""):
        lbl = ctk.CTkLabel(parent, text=f"{self.app.i18n.t(label_key, label_key)}:")
        lbl.grid(row=row, column=col_offset, padx=5, sticky="w")
        if tooltip_key:
            self.bind_i18n_tooltip(lbl, tooltip_key, tooltip_key)
        self.hotkey_labels[config_key] = (lbl, label_key)
        
        current_val = self.app.config.data.get(config_key, "")
        btn = ctk.CTkButton(parent, text=current_val if current_val else self.app.i18n.t("none", "Aucun"), width=80, command=lambda: self.catch_key(config_key, btn, allow_mouse=True))
        btn.grid(row=row, column=col_offset+1, padx=2, pady=2)
        
        self.hotkey_btns[config_key] = btn 
        
        btn_x = ctk.CTkButton(parent, text="✖", width=25, fg_color="#c0392b", hover_color="#e74c3c", command=lambda: self.clear_key(config_key, btn))
        btn_x.grid(row=row, column=col_offset+2, padx=(0, 10))
        self.bind_i18n_tooltip(btn_x, "tooltip_clear_shortcut", "Effacer le raccourci")

    def catch_key(self, config_key, btn, allow_mouse=False):
        if self.is_listening: return
        self.is_listening = True
        mods_now = []
        if win32api.GetAsyncKeyState(win32con.VK_CONTROL) < 0: mods_now.append("ctrl")
        if win32api.GetAsyncKeyState(win32con.VK_MENU) < 0: mods_now.append("alt")
        if win32api.GetAsyncKeyState(win32con.VK_SHIFT) < 0: mods_now.append("shift")
        btn.configure(text="...", fg_color="#f39c12")
        threading.Thread(target=self._listen_hotkey_thread, args=(config_key, btn, allow_mouse, mods_now), daemon=True).start()

    def _listen_hotkey_thread(self, config_key, btn, allow_mouse, mods_before_click=None):
        if mods_before_click is None: mods_before_click = []
        captured_key = None
        captured_mods = []

        def get_current_mods():
            mods = []
            if win32api.GetAsyncKeyState(win32con.VK_CONTROL) < 0: mods.append("ctrl")
            if win32api.GetAsyncKeyState(win32con.VK_MENU) < 0: mods.append("alt")
            if win32api.GetAsyncKeyState(win32con.VK_SHIFT) < 0: mods.append("shift")
            return mods

        while win32api.GetAsyncKeyState(win32con.VK_LBUTTON) < 0 or win32api.GetAsyncKeyState(win32con.VK_RBUTTON) < 0 or win32api.GetAsyncKeyState(win32con.VK_MBUTTON) < 0:
            time.sleep(0.01)
        time.sleep(0.1)

        if not allow_mouse:
            import threading as _threading
            done_event = _threading.Event()
            def on_key_hook(e):
                nonlocal captured_key, captured_mods
                if e.event_type == keyboard.KEY_DOWN:
                    if e.name not in ['alt', 'ctrl', 'shift', 'maj', 'right alt', 'right ctrl', 'left alt', 'left ctrl', 'left shift', 'right shift', 'alt gr', 'menu', 'windows', 'cmd', 'left windows', 'right windows']:
                        current_mods = get_current_mods()
                        combined = list(set(mods_before_click + current_mods))
                        captured_mods = [m for m in ['ctrl', 'alt', 'shift'] if m in combined]
                        mapped_key = self.app.keymaps.scan_to_key_name(e.scan_code)
                        if mapped_key:
                            captured_key = mapped_key
                        else:
                            captured_key = e.name
                        done_event.set()
            hook = keyboard.hook(on_key_hook, suppress=True)
            done_event.wait()
            keyboard.unhook(hook)
        else:
            held_mods = set(mods_before_click)
            MOD_NAMES = {'alt', 'ctrl', 'shift', 'maj', 'right alt', 'right ctrl', 'left alt', 'left ctrl', 'menu'}
            MOD_MAP = {'alt': 'alt', 'left alt': 'alt', 'right alt': 'alt', 'menu': 'alt',
                       'ctrl': 'ctrl', 'left ctrl': 'ctrl', 'right ctrl': 'ctrl',
                       'shift': 'shift', 'maj': 'shift'}

            def on_key(e):
                nonlocal captured_key, captured_mods
                if e.name in MOD_MAP:
                    if e.event_type == keyboard.KEY_DOWN:
                        held_mods.add(MOD_MAP[e.name])
                    elif e.event_type == keyboard.KEY_UP:
                        held_mods.discard(MOD_MAP[e.name])
                    return
                if e.event_type == keyboard.KEY_DOWN:
                    if e.name not in MOD_NAMES:
                        captured_mods = [m for m in ['ctrl', 'alt', 'shift'] if m in held_mods]
                        mapped_key = self.app.keymaps.scan_to_key_name(e.scan_code)
                        if mapped_key:
                            captured_key = mapped_key
                        else: captured_key = e.name
            hook = keyboard.hook(on_key, suppress=True)

            while not captured_key:
                if win32api.GetAsyncKeyState(win32con.VK_LBUTTON) < 0: captured_key = "left_click"
                elif win32api.GetAsyncKeyState(win32con.VK_RBUTTON) < 0: captured_key = "right_click"
                elif win32api.GetAsyncKeyState(win32con.VK_MBUTTON) < 0: captured_key = "middle_click"
                elif win32api.GetAsyncKeyState(0x05) < 0: captured_key = "mouse4"
                elif win32api.GetAsyncKeyState(0x06) < 0: captured_key = "mouse5"

                if captured_key:
                    captured_mods = [m for m in ['ctrl', 'alt', 'shift'] if m in held_mods]
                    break
                time.sleep(0.01)

            keyboard.unhook(hook)

        if captured_key == "esc":
            final_key = self.app.config.data.get(config_key, "")
        else:
            final_key = "+".join(captured_mods) + "+" + captured_key if captured_mods else captured_key

        time.sleep(0.3) 
        self.root.after(0, self.apply_single_hotkey, config_key, final_key, btn)

    def release_modifiers(self):
        try:
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
        except: pass

    def apply_single_hotkey(self, config_key, new_value, btn):
        self.release_modifiers() 
        
        if new_value: 
            for k in list(self.app.config.data.keys()):
                if (k.endswith("_key") or k.endswith("_hotkey")) and k != config_key:
                    if self.app.config.data[k] == new_value:
                        self.app.config.data[k] = ""
                        if k in self.hotkey_btns:
                            self.hotkey_btns[k].configure(text=self.app.i18n.t("none", "Aucun"), fg_color=["#3a7ebf", "#1f538d"])

        self.app.config.data[config_key] = new_value
        self.app.config.save()
        
        btn.configure(text=new_value if new_value else self.app.i18n.t("none", "Aucun"), fg_color=["#3a7ebf", "#1f538d"])
        self.app.setup_hotkeys()
        self.is_listening = False

    def clear_key(self, config_key, btn):
        if self.is_listening: return
        self.apply_single_hotkey(config_key, "", btn)

    def on_version_change(self, choice):
        self.app.config.data["game_version"] = choice
        self.app.config.save()
        if choice == "Rétro":
            self.chk_autofocus.pack(side="left", padx=(15, 5))
        else:
            self.chk_autofocus.pack_forget() 
        self.original_app_refresh()
        self.show_temporary_message(self.app.i18n.t("msg_mode_enabled", "🔄 Mode {choice} activé !").format(choice=choice), "#3498db")

    def on_mode_change(self, choice):
        self.app.logic.set_mode(choice)
        self.app.current_idx = 0

    def get_class_image(self, class_name, is_retro=False):
        filename = f"{class_name}_retro" if is_retro and class_name != "Inconnu" else class_name
        if filename in self.skin_cache: return self.skin_cache[filename]
        path = f"skin/{filename}.png"
        if not os.path.exists(path): return None
        img = ctk.CTkImage(light_image=Image.open(path), dark_image=Image.open(path), size=(24, 24))
        self.skin_cache[filename] = img
        return img

    def change_retro_class(self, name, new_class):
        self.app.config.data["classes"][name] = new_class
        self.app.config.save()
        self.original_app_refresh()

    def set_leader(self, name):
        self.app.logic.set_leader(name)
        self.original_app_refresh()

    def reset_all(self):
        reponse = messagebox.askyesno(self.app.i18n.t("dialog_confirm_title", "Confirmation"),self.app.i18n.t("dialog_reset_text", "Êtes-vous sûr de vouloir tout réinitialiser ?\n\nToutes vos touches seront perdues."))  
        if reponse:
            self.app.config.reset_settings()
            self.original_app_refresh()

    def hide_to_tray(self):
        self.root.withdraw()
        self.is_visible = False
        if self.app.config.data.get("overlay_enabled", True):
            self.app.overlay.show()

    def toggle_visibility(self):
        if self.is_visible:
            self.hide_to_tray()
        else:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.is_visible = True
            self.app.overlay.hide()

    def run(self): self.root.mainloop()

    def open_bind_manager(self):
        CharManagerWindow(self)


class CharManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent_gui):
        super().__init__(parent_gui.root)
        self.parent = parent_gui
        self.app = parent_gui.app
        self.title(self.app.i18n.t("char_manager_title", "⚙️ Gestionnaire de Binds Avancé DOSOFT"))
        self.geometry("620x680")
        self.attributes("-topmost", True)
        self.grab_set() 
        
        self.update_idletasks()
        x = parent_gui.root.winfo_x() + (parent_gui.root.winfo_width() // 2) - (620 // 2)
        y = parent_gui.root.winfo_y() + (parent_gui.root.winfo_height() // 2) - (680 // 2)
        self.geometry(f"+{x}+{y}")

        sub_font = ctk.CTkFont(size=14, slant="italic")
        
        frame_header = ctk.CTkFrame(self)
        frame_header.pack(fill="x", padx=15, pady=15)
        
        frame_mode = ctk.CTkFrame(frame_header, fg_color="transparent")
        frame_mode.pack(fill="x", pady=5)
        ctk.CTkLabel(frame_mode, text=self.app.i18n.t("char_manager_mode", "Mode :"), font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15)
        self.var_mode = ctk.StringVar(value=self.app.config.data.get("advanced_bind_mode", "cycle"))
        seg_mode = ctk.CTkSegmentedButton(frame_mode, values=["cycle", "bind"], variable=self.var_mode, command=self.on_mode_change)
        seg_mode.pack(side="left", padx=5)

        frame_prefix = ctk.CTkFrame(frame_header, fg_color="transparent")
        frame_prefix.pack(fill="x", pady=5)
        ctk.CTkLabel(frame_prefix, text=self.app.i18n.t("char_manager_prefix", "Préfixe Global :"), font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15)
        modifier_value = self.app.config.data.get("advanced_bind_modifier", "ctrl")
        if modifier_value in ("aucun", "nenhum"):
            modifier_value = "none"
        self.var_mod = ctk.StringVar(value=modifier_value)
        seg_mod = ctk.CTkSegmentedButton(frame_prefix, values=["none", "ctrl", "alt", "shift"], variable=self.var_mod)
        seg_mod.pack(side="left", padx=5)
        
        self.frame_desc = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_desc.pack(fill="x", padx=20)
        self.lbl_desc = ctk.CTkLabel(self.frame_desc, text="", font=sub_font, justify="center")
        self.lbl_desc.pack()
        
        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.entry_dict = {} 
        self.buttons_dict = {} 

        btn_save = ctk.CTkButton(self, text=self.app.i18n.t("char_manager_save", "💾 Enregistrer les raccourcis"), fg_color="#27ae60", hover_color="#2ecc71", command=self.save_all)
        btn_save.pack(pady=20)

        self.update_content()

    def on_mode_change(self, value):
        self.app.config.data["advanced_bind_mode"] = value
        self.app.config.save()
        self.update_content()
        self.app.setup_hotkeys()

    def get_base_key(self, bind_str):
        if not bind_str: return ""
        return bind_str.split('+')[-1]

    def catch_key(self, dict_key, btn):
        if self.parent.is_listening: return
        self.parent.is_listening = True
        btn.configure(text="...", fg_color="#f39c12")
        threading.Thread(target=self._listen_thread, args=(dict_key, btn), daemon=True).start()

    def _listen_thread(self, dict_key, btn):
        captured = ""
        def on_key(e):
            nonlocal captured
            if e.event_type == keyboard.KEY_DOWN:
                if e.name not in ['alt', 'ctrl', 'shift', 'maj', 'right alt', 'right ctrl', 'left alt', 'left ctrl', 'left shift', 'right shift', 'alt gr', 'menu', 'windows', 'cmd', 'left windows', 'right windows']:
                    captured = e.name

        hook = keyboard.hook(on_key, suppress=True)
        
        while not captured:
            if win32api.GetAsyncKeyState(0x05) < 0: captured = "mouse4"
            elif win32api.GetAsyncKeyState(0x06) < 0: captured = "mouse5"
            elif win32api.GetAsyncKeyState(0x04) < 0: captured = "middle_click"
            time.sleep(0.01)
            
        keyboard.unhook(hook)
        time.sleep(0.3) 
        self.app.gui.root.after(0, self.apply_key, dict_key, captured, btn)

    def apply_key(self, dict_key, key_name, btn):
        self.parent.release_modifiers()
        if key_name == "esc": key_name = "" 
        
        self.entry_dict[dict_key] = key_name
        btn.configure(text=key_name.upper() if key_name else self.app.i18n.t("none", "Aucun"), fg_color=["#3a7ebf", "#1f538d"])
        self.parent.is_listening = False

    def update_content(self):
        for widget in self.scroll_list.winfo_children(): widget.destroy()
        self.entry_dict = {}
        self.buttons_dict = {}
        
        mode = self.var_mode.get()
        active_list = self.app.logic.get_cycle_list()
        cfg = self.app.config.data

        if mode == "cycle":
            self.lbl_desc.configure(text=self.app.i18n.t("char_manager_desc_cycle", "Target immuable par place. (ex: Ligne 1 focus le 1er de l'initiative)"))
            row_binds = cfg.get("cycle_row_binds", [])
            
            for i in range(8):
                frame_row = ctk.CTkFrame(self.scroll_list)
                frame_row.pack(fill="x", pady=2, padx=5)
                
                current_pseudo = active_list[i]['name'] if i < len(active_list) else "---"
                row_label = self.app.i18n.t("char_manager_position", "Place n°{index}").format(index=i+1)
                ctk.CTkLabel(frame_row, text=row_label, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15, pady=10)
                ctk.CTkLabel(frame_row, text=f"({current_pseudo})", font=ctk.CTkFont(slant="italic")).pack(side="left", padx=5)
                
                try: full_bind = row_binds[i]
                except: full_bind = ""
                base_key = self.get_base_key(full_bind)
                self.entry_dict[i] = base_key
                
                btn = ctk.CTkButton(frame_row, text=base_key.upper() if base_key else self.app.i18n.t("none", "Aucun"), width=80)
                btn.configure(command=lambda k=i, b=btn: self.catch_key(k, b))
                btn.pack(side="right", padx=15, pady=10)
                
                btn_clear = ctk.CTkButton(frame_row, text="✖", width=25, fg_color="#c0392b", hover_color="#e74c3c", command=lambda k=i, b=btn: self.apply_key(k, "esc", b))
                btn_clear.pack(side="right", padx=5)

        elif mode == "bind":
            self.lbl_desc.configure(text=self.app.i18n.t("char_manager_desc_bind", "Target fixe par pseudo (Même s'ils changent d'ordre)"))
            char_binds = cfg.get("persistent_character_binds", {})
            
            if not active_list:
                ctk.CTkLabel(self.scroll_list, text=self.app.i18n.t("char_manager_no_character", "Aucun personnage connecté détecté."), text_color="#e74c3c").pack(pady=50)
                return

            is_retro = self.app.config.data.get("game_version", "Unity") == "Rétro"
            for acc in active_list:
                pseudo = acc['name']
                frame_row = ctk.CTkFrame(self.scroll_list)
                frame_row.pack(fill="x", pady=2, padx=5)
                
                img = self.parent.get_class_image(acc.get('classe', 'Inconnu'), is_retro)
                if img: ctk.CTkLabel(frame_row, text="", image=img).pack(side="left", padx=10, pady=5)
                
                ctk.CTkLabel(frame_row, text=pseudo, font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=5)
                
                full_bind = char_binds.get(pseudo, "")
                base_key = self.get_base_key(full_bind)
                self.entry_dict[pseudo] = base_key
                
                btn = ctk.CTkButton(frame_row, text=base_key.upper() if base_key else self.app.i18n.t("none", "Aucun"), width=80)
                btn.configure(command=lambda k=pseudo, b=btn: self.catch_key(k, b))
                btn.pack(side="right", padx=15, pady=10)
                
                btn_clear = ctk.CTkButton(frame_row, text="✖", width=25, fg_color="#c0392b", hover_color="#e74c3c", command=lambda k=pseudo, b=btn: self.apply_key(k, "esc", b))
                btn_clear.pack(side="right", padx=5)

    def save_all(self):
        mode = self.var_mode.get()
        mod_prefix = self.var_mod.get()
        prefix_str = f"{mod_prefix}+" if mod_prefix != "none" else ""
        
        cfg = self.app.config.data
        cfg["advanced_bind_modifier"] = mod_prefix 
        
        if mode == "cycle":
            new_binds = []
            for i in range(8):
                base = self.entry_dict.get(i, "").lower().strip()
                new_binds.append(prefix_str + base if base else "")
            cfg["cycle_row_binds"] = new_binds

        elif mode == "bind":
            for pseudo, base in self.entry_dict.items():
                base = base.lower().strip()
                cfg["persistent_character_binds"][pseudo] = prefix_str + base if base else ""
            
        self.app.config.save()
        self.parent.show_temporary_message(self.app.i18n.t("msg_binds_saved", "✅ Raccourcis enregistrés avec succès !"), "#2ecc71")
        self.app.setup_hotkeys() 
        self.destroy()
