import os
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox

import customtkinter as ctk
import keyboard
import win32api
from PIL import Image

from i18n import (
    tr,
    get_language_options,
    language_code_from_label,
    language_label,
    get_keyboard_layout_options,
    keyboard_layout_from_label,
    keyboard_layout_label,
)
from keymap import (
    HOTKEY_CONFIG_KEYS,
    convert_hotkey_layout,
    get_key_for_scan,
    normalize_key_name,
)
from utils import resource_path


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

APP_TITLE = "DOSOFT v1.2.2"


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent_gui):
        super().__init__(parent_gui.root)
        self.parent = parent_gui
        self.app = parent_gui.app

        self.title(self.t("⚙️ Paramètres"))
        self.geometry("520x620")
        self.minsize(420, 420)
        self.attributes("-topmost", True)
        self.resizable(True, True)

        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True, padx=5, pady=5)

        title_font = ctk.CTkFont(size=16, weight="bold")
        lang = self.lang

        ctk.CTkLabel(self.scroll_container, text=self.t("Language"), font=title_font).pack(pady=(20, 5))
        frame_lang = ctk.CTkFrame(self.scroll_container)
        frame_lang.pack(fill="x", padx=10, pady=5)

        self.combo_language = ctk.CTkOptionMenu(
            frame_lang,
            values=get_language_options(lang),
            command=self.on_language_change,
        )
        self.combo_language.set(language_label(lang, lang))
        self.combo_language.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(self.scroll_container, text=self.t("Keyboard layout"), font=title_font).pack(pady=(20, 5))
        frame_layout = ctk.CTkFrame(self.scroll_container)
        frame_layout.pack(fill="x", padx=10, pady=5)

        self.combo_layout = ctk.CTkOptionMenu(
            frame_layout,
            values=get_keyboard_layout_options(lang),
            command=self.on_keyboard_layout_change,
        )
        self.combo_layout.set(
            keyboard_layout_label(lang, self.app.config.data.get("keyboard_layout", "qwerty"))
        )
        self.combo_layout.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(self.scroll_container, text=self.t("Roue de Focus (Radiale)"), font=title_font).pack(pady=(20, 5))
        frame_radial = ctk.CTkFrame(self.scroll_container)
        frame_radial.pack(fill="x", padx=10, pady=5)

        self.var_radial = ctk.BooleanVar(value=self.app.config.data.get("radial_menu_active", True))

        sw_radial = ctk.CTkSwitch(
            frame_radial,
            text=self.t("Activer la roue"),
            variable=self.var_radial,
            command=self.save_settings,
        )
        sw_radial.pack(pady=10)

        frame_hk = ctk.CTkFrame(frame_radial, fg_color="transparent")
        frame_hk.pack(pady=(0, 10))

        ctk.CTkLabel(frame_hk, text=self.t("Raccourci :")).pack(side="left", padx=5)

        current_val = self.app.config.data.get("radial_menu_hotkey", "alt+left_click")
        btn_hk = ctk.CTkButton(
            frame_hk,
            text=self.parent.display_hotkey(current_val),
            width=120,
            command=lambda: self.parent.catch_key("radial_menu_hotkey", btn_hk, allow_mouse=True),
        )
        btn_hk.pack(side="left", padx=5)

        self.parent.hotkey_btns["radial_menu_hotkey"] = btn_hk

        ctk.CTkButton(
            frame_hk,
            text="✖",
            width=25,
            fg_color="#c0392b",
            hover_color="#e74c3c",
            command=lambda: self.parent.clear_key("radial_menu_hotkey", btn_hk),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            self.scroll_container,
            text=self.t("Fermer & Sauvegarder"),
            fg_color="#7f8c8d",
            command=self.save_and_close,
        ).pack(pady=(20, 10))

    @property
    def lang(self):
        return self.app.config.data.get("language", "pt")

    def t(self, text, **kwargs):
        return tr(self.app.config, text, **kwargs)

    def _save_config(self, force=False):
        if hasattr(self.app.config, "touch"):
            try:
                self.app.config.touch()
            except Exception:
                pass

        try:
            self.app.config.save(force=force)
        except TypeError:
            self.app.config.save()

    def _convert_all_layout_dependent_binds(self, old_layout, new_layout):
        if old_layout == new_layout:
            return

        for key in HOTKEY_CONFIG_KEYS:
            value = self.app.config.data.get(key)
            if isinstance(value, str) and value:
                self.app.config.data[key] = convert_hotkey_layout(value, old_layout, new_layout)

        row_binds = self.app.config.data.get("cycle_row_binds", [])
        if isinstance(row_binds, list):
            self.app.config.data["cycle_row_binds"] = [
                convert_hotkey_layout(v, old_layout, new_layout) if v else ""
                for v in row_binds
            ]

        char_binds = self.app.config.data.get("persistent_character_binds", {})
        if isinstance(char_binds, dict):
            self.app.config.data["persistent_character_binds"] = {
                pseudo: convert_hotkey_layout(bind, old_layout, new_layout) if bind else ""
                for pseudo, bind in char_binds.items()
            }

    def save_settings(self):
        self.app.config.data["radial_menu_active"] = self.var_radial.get()
        self._save_config()
        self.app.setup_hotkeys()

    def on_language_change(self, choice):
        old_lang = self.app.config.data.get("language", "pt")
        new_lang = language_code_from_label(choice)

        if new_lang == old_lang:
            return

        self.app.config.data["radial_menu_active"] = self.var_radial.get()
        self.app.config.data["language"] = new_lang
        self._save_config(force=True)

        self.after(150, self.app.restart_app)

    def on_keyboard_layout_change(self, choice):
        old_layout = self.app.config.data.get("keyboard_layout", "qwerty")
        new_layout = keyboard_layout_from_label(choice)

        if new_layout == old_layout:
            return

        self.app.config.data["radial_menu_active"] = self.var_radial.get()
        self._convert_all_layout_dependent_binds(old_layout, new_layout)
        self.app.config.data["keyboard_layout"] = new_layout
        self._save_config(force=True)

        self.after(150, self.app.restart_app)

    def save_and_close(self):
        self.save_settings()
        self.destroy()


class BindManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent_gui):
        super().__init__(parent_gui.root)
        self.parent = parent_gui
        self.app = parent_gui.app

        self.title(self.t("Raccourcis Clavier"))
        self.geometry("700x650")
        self.minsize(560, 460)
        self.attributes("-topmost", True)

        self.entry_dict = {}

        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            header,
            text=self.t("Raccourcis Clavier"),
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left", padx=10, pady=10)

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        controls = ctk.CTkFrame(body)
        controls.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(controls, text=self.t("Mode :")).pack(side="left", padx=(10, 5))
        self.var_mode = ctk.StringVar(value=self.app.config.data.get("advanced_bind_mode", "cycle"))
        self.combo_mode = ctk.CTkOptionMenu(
            controls,
            values=["cycle", "bind"],
            variable=self.var_mode,
            command=self.on_mode_change,
            width=120,
        )
        self.combo_mode.pack(side="left", padx=5)

        ctk.CTkLabel(controls, text=self.t("Modificateur :")).pack(side="left", padx=(20, 5))
        self.var_mod = ctk.StringVar(
            value=self._display_modifier(self.app.config.data.get("advanced_bind_modifier", "none"))
        )
        self.combo_mod = ctk.CTkOptionMenu(
            controls,
            values=["ctrl", "alt", "shift", self.t("Aucun")],
            variable=self.var_mod,
            width=120,
        )
        self.combo_mod.pack(side="left", padx=5)

        self.lbl_desc = ctk.CTkLabel(body, text="", justify="left")
        self.lbl_desc.pack(fill="x", padx=15, pady=(0, 8))

        self.scroll_list = ctk.CTkScrollableFrame(body)
        self.scroll_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            footer,
            text=self.t("Fermer"),
            command=self.destroy,
            fg_color="#7f8c8d",
            hover_color="#95a5a6",
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            footer,
            text=self.t("Fermer & Sauvegarder"),
            command=self.save_all,
            fg_color="#27ae60",
            hover_color="#2ecc71",
        ).pack(side="right", padx=5)

        self.update_content()

    def t(self, text, **kwargs):
        return tr(self.app.config, text, **kwargs)

    def _save_config(self, force=False):
        if hasattr(self.app.config, "touch"):
            try:
                self.app.config.touch()
            except Exception:
                pass

        try:
            self.app.config.save(force=force)
        except TypeError:
            self.app.config.save()

    def _display_modifier(self, value):
        value = (value or "none").strip().lower()
        if value == "none":
            return self.t("Aucun")
        return value

    def _normalize_modifier(self, value):
        value = (value or "").strip().lower()
        if value in {"none", "aucun", "nenhum", self.t("Aucun").lower()}:
            return "none"
        if value in {"ctrl", "alt", "shift"}:
            return value
        return "ctrl"

    def on_mode_change(self, value):
        self.app.config.data["advanced_bind_mode"] = value
        self._save_config()
        self.update_content()

    def get_base_key(self, bind_str):
        if not bind_str:
            return ""
        return bind_str.split("+")[-1]

    def catch_key(self, dict_key, btn):
        if self.parent.is_listening:
            return

        self.parent.is_listening = True
        btn.configure(text="...", fg_color="#f39c12")
        threading.Thread(target=self._listen_thread, args=(dict_key, btn), daemon=True).start()

    def _listen_thread(self, dict_key, btn):
        captured = ""
        layout = self.parent.current_layout()

        ignored = {
            "alt", "ctrl", "shift", "maj",
            "right alt", "right ctrl", "left alt", "left ctrl",
            "menu", "windows", "cmd",
        }

        def on_key(e):
            nonlocal captured
            if e.event_type == keyboard.KEY_DOWN and e.name not in ignored:
                fallback = normalize_key_name(e.name)
                captured = get_key_for_scan(layout, e.scan_code, fallback)

        hook = keyboard.hook(on_key, suppress=True)

        while not captured:
            if win32api.GetAsyncKeyState(0x05) < 0:
                captured = "mouse4"
            elif win32api.GetAsyncKeyState(0x06) < 0:
                captured = "mouse5"
            elif win32api.GetAsyncKeyState(0x04) < 0:
                captured = "middle_click"
            time.sleep(0.01)

        keyboard.unhook(hook)
        time.sleep(0.2)
        self.parent.root.after(0, self.apply_key, dict_key, captured, btn)

    def apply_key(self, dict_key, key_name, btn):
        self.parent.app.release_modifiers()

        if key_name == "esc":
            key_name = ""

        self.entry_dict[dict_key] = key_name
        btn.configure(
            text=key_name.upper() if key_name else self.t("Aucun"),
            fg_color=["#3a7ebf", "#1f538d"],
        )
        self.parent.is_listening = False

    def _build_cycle_rows(self):
        self.lbl_desc.configure(
            text=self.t("Target immuable par place. (ex: Ligne 1 focus le 1er de l'initiative)")
        )

        active_list = self.app.logic.get_cycle_list()
        row_binds = self.app.config.data.get("cycle_row_binds", [])

        for i in range(8):
            frame_row = ctk.CTkFrame(self.scroll_list)
            frame_row.pack(fill="x", pady=4, padx=5)

            current_pseudo = active_list[i]["name"] if i < len(active_list) else "---"

            ctk.CTkLabel(
                frame_row,
                text=self.t("Place n°{index}", index=i + 1),
                font=ctk.CTkFont(weight="bold"),
                width=110,
                anchor="w",
            ).pack(side="left", padx=(15, 5), pady=10)

            ctk.CTkLabel(
                frame_row,
                text=f"({current_pseudo})",
                font=ctk.CTkFont(slant="italic"),
                anchor="w",
            ).pack(side="left", padx=5)

            full_bind = row_binds[i] if i < len(row_binds) else ""
            base_key = self.get_base_key(full_bind)
            self.entry_dict[i] = base_key

            btn = ctk.CTkButton(
                frame_row,
                text=base_key.upper() if base_key else self.t("Aucun"),
                width=90,
            )
            btn.configure(command=lambda k=i, b=btn: self.catch_key(k, b))
            btn.pack(side="right", padx=15, pady=10)

            btn_clear = ctk.CTkButton(
                frame_row,
                text="✖",
                width=28,
                fg_color="#c0392b",
                hover_color="#e74c3c",
            )
            btn_clear.configure(command=lambda k=i, b=btn: self.apply_key(k, "esc", b))
            btn_clear.pack(side="right", padx=5)

    def _build_bind_rows(self):
        self.lbl_desc.configure(
            text=self.t("Target fixe par pseudo (Même s'ils changent d'ordre)")
        )

        detected_accounts = list(self.app.logic.all_accounts)
        char_binds = self.app.config.data.get("persistent_character_binds", {})

        if not detected_accounts:
            ctk.CTkLabel(
                self.scroll_list,
                text=self.t("Aucun personnage connecté détecté."),
                text_color="#e74c3c",
            ).pack(pady=50)
            return

        is_retro = self.app.config.data.get("game_version", "Unity") == "Rétro"

        for acc in detected_accounts:
            pseudo = acc["name"]

            frame_row = ctk.CTkFrame(self.scroll_list)
            frame_row.pack(fill="x", pady=4, padx=5)

            img = self.parent.get_class_image(acc.get("classe", "Inconnu"), is_retro)
            if img:
                ctk.CTkLabel(frame_row, text="", image=img).pack(side="left", padx=(10, 5), pady=6)

            ctk.CTkLabel(
                frame_row,
                text=pseudo,
                font=ctk.CTkFont(size=15, weight="bold"),
                anchor="w",
            ).pack(side="left", padx=5)

            full_bind = char_binds.get(pseudo, "")
            base_key = self.get_base_key(full_bind)
            self.entry_dict[pseudo] = base_key

            btn = ctk.CTkButton(
                frame_row,
                text=base_key.upper() if base_key else self.t("Aucun"),
                width=90,
            )
            btn.configure(command=lambda k=pseudo, b=btn: self.catch_key(k, b))
            btn.pack(side="right", padx=15, pady=10)

            btn_clear = ctk.CTkButton(
                frame_row,
                text="✖",
                width=28,
                fg_color="#c0392b",
                hover_color="#e74c3c",
            )
            btn_clear.configure(command=lambda k=pseudo, b=btn: self.apply_key(k, "esc", b))
            btn_clear.pack(side="right", padx=5)

    def update_content(self):
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        self.entry_dict = {}

        # Garante lista atualizada ao abrir a janela
        if not self.app.logic.all_accounts:
            try:
                self.app.logic.scan_slots()
            except Exception:
                pass

        mode = self.var_mode.get()

        if mode == "cycle":
            self._build_cycle_rows()
        else:
            self._build_bind_rows()

    def save_all(self):
        mode = self.var_mode.get()
        modifier = self._normalize_modifier(self.var_mod.get())

        self.app.config.data["advanced_bind_mode"] = mode
        self.app.config.data["advanced_bind_modifier"] = modifier

        if mode == "cycle":
            binds = []
            for i in range(8):
                base_key = self.entry_dict.get(i, "")
                binds.append(base_key if base_key else "")
            self.app.config.data["cycle_row_binds"] = binds

        elif mode == "bind":
            char_binds = {}
            for pseudo, key_name in self.entry_dict.items():
                if key_name:
                    char_binds[pseudo] = key_name
            self.app.config.data["persistent_character_binds"] = char_binds

        self._save_config()
        self.app.setup_hotkeys()
        self.parent.show_temporary_message(self.t("✅ Raccourcis sauvegardés !"), "#2ecc71")
        self.destroy()


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

        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self.is_listening = False
        self.is_visible = True
        self.hotkey_btns = {}
        self.skin_cache = {}

        cfg = self.app.config.data
        self.var_tooltips = ctk.BooleanVar(value=cfg.get("show_tooltips", True))
        self.var_autofocus = ctk.BooleanVar(value=cfg.get("auto_focus_retro", False))

        self._build_tooltip()
        self._build_layout()

    def t(self, text, **kwargs):
        return tr(self.app.config, text, **kwargs)

    def current_layout(self):
        return self.app.config.data.get("keyboard_layout", "qwerty")

    def _save_config(self, force=False):
        if hasattr(self.app.config, "touch"):
            try:
                self.app.config.touch()
            except Exception:
                pass

        try:
            self.app.config.save(force=force)
        except TypeError:
            self.app.config.save()

    def _build_tooltip(self):
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.overrideredirect(True)
        self.tooltip.attributes("-topmost", True)
        self.tooltip_lbl = tk.Label(
            self.tooltip,
            text="",
            fg="#ecf0f1",
            bg="#2c3e50",
            font=("Segoe UI", 9),
            padx=6,
            pady=3,
            relief="solid",
            borderwidth=1,
        )
        self.tooltip_lbl.pack()
        self.tooltip.withdraw()

    def _build_layout(self):
        cfg = self.app.config.data

        self.header_f = ctk.CTkFrame(self.root, fg_color="transparent")
        self.header_f.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            self.header_f,
            text=APP_TITLE,
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")

        self.btn_settings = ctk.CTkButton(
            self.header_f,
            text=self.t("⚙️ Paramètres"),
            fg_color="#34495e",
            hover_color="#2c3e50",
            width=120,
            command=self.open_settings,
        )
        self.btn_settings.pack(side="right")
        self.bind_tooltip(self.btn_settings, self.t("Paramètres du jeu et de la roue"))

        self.btn_tuto = ctk.CTkButton(
            self.header_f,
            text=self.t("🎓 Tuto"),
            fg_color="#8e44ad",
            hover_color="#9b59b6",
            width=80,
            command=self.launch_tutorial,
        )
        self.btn_tuto.pack(side="right", padx=(0, 10))

        self.btn_off = ctk.CTkButton(
            self.header_f,
            text="🔴 OFF",
            fg_color="#c0392b",
            hover_color="#e74c3c",
            width=60,
            command=self.app.quit_app,
        )
        self.btn_off.pack(side="right", padx=(0, 10))
        self.bind_tooltip(self.btn_off, self.t("Shutdown complet : Force la fermeture immédiate de DOSOFT"))

        self.frame_mode = ctk.CTkFrame(self.root)
        self.frame_mode.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(self.frame_mode, text=self.t("Contrôler :")).pack(side="left", padx=10, pady=5)

        self.combo_mode = ctk.CTkOptionMenu(
            self.frame_mode,
            values=["ALL", "Team 1", "Team 2"],
            command=self.on_mode_change,
        )
        self.combo_mode.set(cfg.get("current_mode", "ALL"))
        self.combo_mode.pack(side="left", padx=5, pady=5)

        ctk.CTkLabel(self.frame_mode, text=self.t("Versions :")).pack(side="left", padx=(20, 5), pady=5)

        self.combo_version = ctk.CTkOptionMenu(
            self.frame_mode,
            values=["Unity", "Rétro"],
            width=100,
            fg_color="#8e44ad",
            button_color="#9b59b6",
            button_hover_color="#8e44ad",
            command=self.on_version_change,
        )
        self.combo_version.set(cfg.get("game_version", "Unity"))
        self.combo_version.pack(side="left", padx=5, pady=5)

        self.chk_autofocus = ctk.CTkCheckBox(
            self.frame_mode,
            text=self.t("Auto-Focus 🔔"),
            variable=self.var_autofocus,
            command=self.toggle_autofocus,
            width=110,
        )

        if cfg.get("game_version", "Unity") == "Rétro":
            self.chk_autofocus.pack(side="left", padx=(15, 5))

        self.bind_tooltip(self.chk_autofocus, self.t("Focus automatiquement la page Rétro lors d'une notification"))

        self.frame_keys = ctk.CTkFrame(self.root)
        self.frame_keys.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(
            self.frame_keys,
            text=self.t("Raccourcis Clavier"),
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, columnspan=6, pady=5)

        self.create_hotkey_row(
            self.frame_keys,
            self.t("Précédent"),
            "prev_key",
            1,
            0,
            self.t("Focus perso précédent"),
        )
        self.create_hotkey_row(
            self.frame_keys,
            self.t("Suivant"),
            "next_key",
            1,
            3,
            self.t("Focus perso suivant"),
        )
        self.create_hotkey_row(
            self.frame_keys,
            self.t("Chef"),
            "leader_key",
            2,
            0,
            self.t("Reprendre focus sur le Chef"),
        )
        self.create_hotkey_row(
            self.frame_keys,
            self.t("Afficher/Cacher"),
            "toggle_app_key",
            2,
            3,
            self.t("Masquer/Afficher l'app"),
        )

        self.frame_actions = ctk.CTkFrame(self.root)
        self.frame_actions.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(self.frame_actions, text=self.t("🔊 Volume Roulette :")).pack(side="left", padx=10)

        self.slider_volume = ctk.CTkSlider(
            self.frame_actions,
            from_=0,
            to=100,
            command=self.on_volume_change,
            width=150,
        )
        self.slider_volume.set(cfg.get("volume_level", 50))
        self.slider_volume.pack(side="left", padx=10, pady=10)

        ctk.CTkButton(
            self.frame_actions,
            text=self.t("Fermer Team"),
            fg_color="#c0392b",
            hover_color="#e74c3c",
            command=self.close_all_and_refresh,
            width=120,
        ).pack(side="right", padx=10)

        ctk.CTkButton(
            self.frame_actions,
            text=self.t("Reset Settings"),
            fg_color="#7f8c8d",
            hover_color="#95a5a6",
            command=self.reset_all,
            width=120,
        ).pack(side="right", padx=10)

        pill_frame = ctk.CTkFrame(self.root, fg_color="#3b4252", corner_radius=8)
        pill_frame.pack(fill="x", padx=15, pady=(10, 0), ipadx=5, ipady=2)

        ctk.CTkLabel(
            pill_frame,
            text=self.t("Comptes actifs"),
            font=ctk.CTkFont(size=13, weight="normal"),
            text_color="#ecf0f1",
        ).pack(side="left", padx=10, pady=4)

        btn_manage_binds = ctk.CTkButton(
            pill_frame,
            text="⚙️",
            width=28,
            height=28,
            fg_color="#2c3e50",
            hover_color="#1a252f",
            corner_radius=6,
            command=self.open_bind_manager,
        )
        btn_manage_binds.pack(side="right", padx=5, pady=4)
        self.bind_tooltip(btn_manage_binds, self.t("Gérer les raccourcis avancés par personnage"))

        self.scroll_frame = ctk.CTkScrollableFrame(self.root)
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=(5, 10))

        self.frame_footer = ctk.CTkFrame(self.root, fg_color="transparent")
        self.frame_footer.pack(side="bottom", fill="x", padx=15, pady=(0, 15))

        ctk.CTkButton(
            self.frame_footer,
            text=self.t("Rafraîchir"),
            command=self.original_app_refresh,
            width=80,
        ).pack(side="left")

        self.btn_sort_win = ctk.CTkButton(
            self.frame_footer,
            text=self.t("Trier Barre Windows"),
            fg_color="#8e44ad",
            hover_color="#9b59b6",
            command=self.trigger_sort_taskbar,
            width=120,
        )
        self.btn_sort_win.pack(side="left", padx=5)

        chk_tooltips = ctk.CTkCheckBox(
            self.frame_footer,
            text=self.t("Bulles"),
            variable=self.var_tooltips,
            command=self.toggle_tooltips_setting,
            width=60,
        )
        chk_tooltips.pack(side="left", padx=15)

        ctk.CTkButton(
            self.frame_footer,
            text=self.t("Cacher l'UI"),
            command=self.toggle_visibility,
            fg_color="transparent",
            border_width=1,
            width=70,
        ).pack(side="right")

        frame_msg = ctk.CTkFrame(self.root, fg_color="transparent", height=20)
        frame_msg.pack(fill="x", padx=15, pady=(0, 5))
        self.lbl_feedback = ctk.CTkLabel(frame_msg, text="", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_feedback.pack(expand=True)

    def display_hotkey(self, value):
        return value if value else self.t("Aucun")

    def open_settings(self):
        if not hasattr(self, "settings_window") or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self)
        else:
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_force()

    def open_bind_manager(self):
        if not hasattr(self, "bind_manager") or not self.bind_manager.winfo_exists():
            self.bind_manager = BindManagerWindow(self)
        else:
            self.bind_manager.deiconify()
            self.bind_manager.lift()
            self.bind_manager.focus_force()

    def launch_tutorial(self):
        if not self.app.config.data.get("tutorial_done", False):
            self.app.config.data["tutorial_done"] = True
            self._save_config()

        rep = messagebox.askyesno(
            self.t("Tutoriel Vidéo"),
            self.t("Voulez-vous ouvrir la vidéo de présentation sur YouTube ?"),
        )
        if rep:
            webbrowser.open("")

    def toggle_from_tray(self, icon=None, item=None):
        self.root.after(0, self.toggle_visibility)

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
        self.show_temporary_message(self.t("🚀 Les pages ont été rangées avec succès !"), "#9b59b6")

    def close_and_refresh(self, name):
        def _close():
            self.app.logic.close_account_window(name)
            time.sleep(0.5)
            self.root.after(0, self.original_app_refresh)

        threading.Thread(target=_close, daemon=True).start()

    def close_all_and_refresh(self):
        def _close_all():
            self.app.logic.close_all_active_accounts()
            time.sleep(0.5)
            self.root.after(0, self.original_app_refresh)
            self.root.after(0, self.show_temporary_message, self.t("💥 La team a été fermée !"), "#e74c3c")

        threading.Thread(target=_close_all, daemon=True).start()

    def toggle_tooltips_setting(self):
        self.app.config.data["show_tooltips"] = self.var_tooltips.get()
        self._save_config()
        if not self.var_tooltips.get():
            self.tooltip.withdraw()

    def bind_tooltip(self, widget, text):
        def on_enter(event):
            if self.is_listening or not self.app.config.data.get("show_tooltips", True):
                return
            self.tooltip_lbl.config(text=text)
            self.tooltip.deiconify()
            x, y = win32api.GetCursorPos()
            self.tooltip.geometry(f"+{x + 15}+{y + 15}")

        def on_leave(event):
            if not self.is_listening:
                self.tooltip.withdraw()

        def on_motion(event):
            if self.is_listening or not self.app.config.data.get("show_tooltips", True):
                return
            x, y = win32api.GetCursorPos()
            self.tooltip.geometry(f"+{x + 15}+{y + 15}")

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        widget.bind("<Motion>", on_motion)

    def toggle_team_ui(self, name, button_widget):
        current = self.app.config.data["accounts_team"].get(name, "Team 1")
        new_team = "Team 2" if current == "Team 1" else "Team 1"
        self.app.logic.change_team(name, new_team)
        button_widget.configure(
            text="T1" if new_team == "Team 1" else "T2",
            fg_color="#2980b9" if new_team == "Team 1" else "#c0392b",
        )
        self.original_app_refresh()

    def set_leader(self, name):
        self.app.logic.set_leader(name)
        self.original_app_refresh()

    def toggle_autofocus(self):
        self.app.config.data["auto_focus_retro"] = self.var_autofocus.get()
        self._save_config()

    def on_volume_change(self, value):
        self.app.update_volume(int(value))

    def create_hotkey_row(self, parent, label_text, config_key, row, col_offset, tooltip_txt=""):
        lbl = ctk.CTkLabel(parent, text=f"{label_text}:")
        lbl.grid(row=row, column=col_offset, padx=5, sticky="w")
        if tooltip_txt:
            self.bind_tooltip(lbl, tooltip_txt)

        current_val = self.app.config.data.get(config_key, "")
        btn = ctk.CTkButton(
            parent,
            text=self.display_hotkey(current_val),
            width=80,
            command=lambda: self.catch_key(config_key, btn),
        )
        btn.grid(row=row, column=col_offset + 1, padx=5, pady=5)
        self.hotkey_btns[config_key] = btn

        btn_clear = ctk.CTkButton(
            parent,
            text="✖",
            width=25,
            fg_color="#c0392b",
            hover_color="#e74c3c",
            command=lambda: self.clear_key(config_key, btn),
        )
        btn_clear.grid(row=row, column=col_offset + 2, padx=5)

    def catch_key(self, config_key, btn, allow_mouse=True):
        if self.is_listening:
            return

        self.is_listening = True
        btn.configure(text="...", fg_color="#f39c12")
        threading.Thread(
            target=self._listen_hotkey_thread,
            args=(config_key, btn, allow_mouse),
            daemon=True,
        ).start()

    def _listen_hotkey_thread(self, config_key, btn, allow_mouse):
        captured = ""
        layout = self.current_layout()

        ignored = {
            "alt", "ctrl", "shift", "maj",
            "right alt", "right ctrl", "left alt", "left ctrl",
            "menu", "windows", "cmd",
        }

        def on_key(e):
            nonlocal captured
            if e.event_type == keyboard.KEY_DOWN and e.name not in ignored:
                fallback = normalize_key_name(e.name)
                captured = get_key_for_scan(layout, e.scan_code, fallback)

        hook = keyboard.hook(on_key, suppress=True)

        while not captured:
            if allow_mouse:
                if win32api.GetAsyncKeyState(0x05) < 0:
                    captured = "mouse4"
                elif win32api.GetAsyncKeyState(0x06) < 0:
                    captured = "mouse5"
                elif win32api.GetAsyncKeyState(0x01) < 0:
                    captured = "left_click"
                elif win32api.GetAsyncKeyState(0x02) < 0:
                    captured = "right_click"
                elif win32api.GetAsyncKeyState(0x04) < 0:
                    captured = "middle_click"
            time.sleep(0.01)

        keyboard.unhook(hook)
        time.sleep(0.2)
        self.root.after(0, self.apply_key, config_key, captured, btn)

    def apply_key(self, config_key, key_name, btn):
        self.app.release_modifiers()
        if key_name == "esc":
            key_name = ""

        self.app.config.data[config_key] = key_name
        self._save_config()
        btn.configure(text=self.display_hotkey(key_name), fg_color=["#3a7ebf", "#1f538d"])
        self.is_listening = False
        self.app.setup_hotkeys()

    def clear_key(self, config_key, btn):
        self.app.config.data[config_key] = ""
        self._save_config()
        btn.configure(text=self.t("Aucun"), fg_color=["#3a7ebf", "#1f538d"])
        self.app.setup_hotkeys()

    def get_class_image(self, class_name, is_retro=False):
        filename = f"{class_name}_retro" if is_retro and class_name != "Inconnu" else class_name
        if filename in self.skin_cache:
            return self.skin_cache[filename]

        path = resource_path("skin", f"{filename}.png")
        if not os.path.exists(path):
            return None

        try:
            img = Image.open(path).resize((26, 26), Image.Resampling.LANCZOS)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(26, 26))
            self.skin_cache[filename] = photo
            return photo
        except Exception:
            return None

    def refresh_list(self, accounts):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not accounts:
            ctk.CTkLabel(
                self.scroll_frame,
                text=self.t("Aucun compte détecté."),
                text_color="#e74c3c",
            ).pack(pady=40)
            return

        leader_name = self.app.config.data.get("leader_name", "")
        is_retro = self.app.config.data.get("game_version", "Unity") == "Rétro"

        for idx, acc in enumerate(accounts):
            row_frame = ctk.CTkFrame(self.scroll_frame)
            row_frame.pack(fill="x", padx=5, pady=3)

            img = self.get_class_image(acc.get("classe", "Inconnu"), is_retro)
            if img:
                ctk.CTkLabel(row_frame, text="", image=img).pack(side="left", padx=(8, 6), pady=8)

            text_color = "#ecf0f1" if acc.get("active", True) else "#7f8c8d"
            ctk.CTkLabel(
                row_frame,
                text=acc["name"],
                text_color=text_color,
                font=ctk.CTkFont(size=15, weight="bold"),
            ).pack(side="left", padx=(5, 6))

            classe = acc.get("classe", "Inconnu")
            ctk.CTkLabel(
                row_frame,
                text=f"[{classe}]",
                text_color="#95a5a6",
                font=ctk.CTkFont(size=13),
            ).pack(side="left", padx=5)

            var_active = tk.BooleanVar(value=acc.get("active", True))
            chk = ctk.CTkCheckBox(
                row_frame,
                text="",
                variable=var_active,
                width=24,
                command=lambda n=acc["name"], v=var_active: self.on_toggle_account(n, v.get()),
            )
            chk.pack(side="right", padx=8)
            self.bind_tooltip(chk, self.t("Activer/Désactiver le compte"))

            btn_close = ctk.CTkButton(
                row_frame,
                text="✖",
                width=30,
                fg_color="#c0392b",
                hover_color="#e74c3c",
                command=lambda n=acc["name"]: self.close_and_refresh(n),
            )
            btn_close.pack(side="right", padx=4)
            self.bind_tooltip(btn_close, self.t("Fermer la fenêtre"))

            is_leader = acc["name"] == leader_name
            btn_lead = ctk.CTkButton(
                row_frame,
                text="🌟" if is_leader else "☆",
                width=35,
                fg_color="#f39c12" if is_leader else "transparent",
                border_width=1,
                command=lambda n=acc["name"]: self.set_leader(n),
            )
            btn_lead.pack(side="right", padx=2)
            self.bind_tooltip(btn_lead, self.t("Définir comme Chef"))

            team_val = acc.get("team", "Team 1")
            btn_team = ctk.CTkButton(
                row_frame,
                text="T1" if team_val == "Team 1" else "T2",
                width=35,
                fg_color="#2980b9" if team_val == "Team 1" else "#c0392b",
            )
            btn_team.configure(command=lambda n=acc["name"], b=btn_team: self.toggle_team_ui(n, b))
            btn_team.pack(side="right", padx=5)
            self.bind_tooltip(btn_team, self.t("Changer l'équipe"))

            btn_down = ctk.CTkButton(
                row_frame,
                text="▼",
                width=25,
                fg_color="#34495e",
                hover_color="#2c3e50",
                command=lambda n=acc["name"]: self.move_row(n, 1),
            )
            btn_down.pack(side="right", padx=(2, 10))
            self.bind_tooltip(btn_down, self.t("Descendre"))

            btn_up = ctk.CTkButton(
                row_frame,
                text="▲",
                width=25,
                fg_color="#34495e",
                hover_color="#2c3e50",
                command=lambda n=acc["name"]: self.move_row(n, -1),
            )
            btn_up.pack(side="right", padx=2)
            self.bind_tooltip(btn_up, self.t("Monter"))

            pos_values = [str(i + 1) for i in range(len(accounts))]
            combo_pos = ctk.CTkOptionMenu(
                row_frame,
                values=pos_values,
                width=50,
                height=24,
                fg_color="#34495e",
                button_color="#2c3e50",
                button_hover_color="#1a252f",
            )
            combo_pos.set(str(idx + 1))
            combo_pos.configure(command=lambda val, n=acc["name"]: self.change_position(n, val))
            combo_pos.pack(side="right", padx=(2, 5))
            self.bind_tooltip(combo_pos, self.t("Position exacte"))

    def on_toggle_account(self, name, is_active):
        self.app.logic.toggle_account(name, is_active)
        self.original_app_refresh()

    def on_mode_change(self, value):
        self.app.logic.set_mode(value)
        self.original_app_refresh()

    def on_version_change(self, value):
        self.app.config.data["game_version"] = value
        self._save_config()

        if value == "Rétro":
            self.chk_autofocus.pack(side="left", padx=(15, 5))
        else:
            self.chk_autofocus.pack_forget()

        self.original_app_refresh()

    def hide_to_tray(self):
        self.root.withdraw()
        self.is_visible = False

    def toggle_visibility(self):
        if self.root.state() == "withdrawn":
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.is_visible = True
        else:
            self.hide_to_tray()

    def reset_all(self):
        rep = messagebox.askyesno(
            self.t("Reset Settings"),
            self.t("Voulez-vous vraiment réinitialiser toute la configuration ?"),
        )
        if not rep:
            return

        self.app.config.reset_settings()
        self.app.setup_hotkeys()
        self.original_app_refresh()
        self.show_temporary_message(self.t("✅ Configuration réinitialisée !"), "#2ecc71")
        self.root.after(250, self.app.restart_app)

    def run(self):
        self.root.mainloop()