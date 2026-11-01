import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import keyboard
import threading
import time
import os
import json
import queue
from copy import deepcopy
import win32api
import win32con
from PIL import Image, ImageTk, ImageDraw
from i18n_manager import I18nManager, LANGUAGE_NAMES
from config_manager import Config
from dofus_settings_manager import DofusSettingsError
from app_version import APP_TITLE
from resource_paths import resource_path, skin_path
from retro_debug import get_retro_debug_log_path, write_retro_debug
from hotkey_debug import write_hotkey_debug
from hotkey_policy import (
    assignment_conflict,
    describe_conflicts,
    find_hotkey_conflicts,
    normalize_hotkey,
)
from obs_icon_catalog import DEFAULT_OBS_ICON, OBS_ICON_CATALOG, OBS_ICON_LABELS, obs_icon_path
from dosoft_obs_bridge import PROFILE_VERSION
from streamdeck_model import (
    move_streamdeck_control,
    ordered_streamdeck_controls,
    remove_streamdeck_control,
)
from windows_process import is_process_running


ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")  


def ui_text(app, key, default, **values):
    """Translate visible UI text and safely interpolate optional values."""
    text = app.i18n.t(key, default)
    if not values:
        return text
    try:
        return text.format(**values)
    except (KeyError, ValueError, IndexError):
        return text

UNITY_THEMES = {
    # Nouveau visuel Unity : thème par défaut de la bêta.
    "1": {
        "background": "#111225", "panel": "#20213d", "panel_alt": "#35375c",
        "accent": "#9ebd05", "accent_hover": "#bfdc1c", "border": "#b9e936",
        "title": "#f0f0ff", "muted": "#c6c6e8", "banner": "#282948",
        "toast": "#2a2d4c", "clear": "#a3434d", "clear_hover": "#c95862",
        "background_image": "unity_arcane_texture.png",
        "module_surface": True,
        "focus_icon": "focus", "volume_icon": "volume",
        "follow_icon": "follow", "group_icon": "groupe",
    },
    # Aspect Unity historique, conservé sans modification comme alternative.
    "2": {
        "background": "#1f2933", "panel": "#283845", "panel_alt": "#34495e",
        "accent": "#2f80c3", "accent_hover": "#3e95d5", "border": "#78b9e8",
        "title": "#d8efff", "muted": "#b7c9d6",
    },
}

GAME_THEMES = {
    "Unity": UNITY_THEMES["1"],
    "Rétro": {
        "background": "#2d2822", "panel": "#40382d", "panel_alt": "#554836",
        "accent": "#9a6a3f", "accent_hover": "#b27c4a", "border": "#e0bd78",
        "title": "#f2ddaf", "muted": "#d0bea0",
    },
}

# Chaque direction artistique WAKFU possède ses couleurs et ses ressources.
# Le thème 1 est le visuel actuel ; les prochains thèmes pourront s'ajouter ici
# sans modifier les comportements du sélecteur.
WAKFU_THEMES = {
    "1": {
        "background": "#101519", "panel": "#171d21", "panel_alt": "#263137",
        "accent": "#176c7c", "accent_hover": "#23889a", "border": "#c2a468",
        "title": "#f2e5c2", "muted": "#b9c6c2", "banner": "#152228",
        "toast": "#172126", "clear": "#9a3935", "clear_hover": "#b94c45",
        "background_image": "wakfu_panel_texture.png",
        "focus_icon": "focus", "volume_icon": "volume",
        "follow_icon": "follow", "group_icon": "groupe",
    },
    "2": {
        "background": "#080616", "panel": "#121329", "panel_alt": "#2a1d50",
        "accent": "#7447d5", "accent_hover": "#9a6df2", "border": "#46d8ed",
        "title": "#f1e9ff", "muted": "#c5bedf", "banner": "#181035",
        "toast": "#1a1240", "clear": "#8f315f", "clear_hover": "#bc497d",
        "background_image": "espace.jpg",
        "focus_icon": "focus", "volume_icon": "volume",
        "follow_icon": "follow", "group_icon": "groupe",
    },
}

RETRO_THEMES = {
    "1": {
        # Même hiérarchie que le thème WAKFU : fond texturé respirant, cartes
        # sombres, bordures dorées et boutons orange. Le parchemin ne sert plus
        # de gros aplat clair derrière les modules.
        "background": "#201d17", "panel": "#302d24", "panel_alt": "#49412f",
        "accent": "#bb6a24", "accent_hover": "#dc8432", "border": "#d9bd79",
        "title": "#f2e4bb", "muted": "#d4c69f", "banner": "#3a3427",
        "toast": "#40392a", "clear": "#9b4030", "clear_hover": "#c25740",
        "background_image": "retro_parchment_texture.png",
        "focus_icon": "focus", "volume_icon": "volume",
        "follow_icon": "follow", "group_icon": "groupe",
    },
}


def selected_game_theme(config):
    if config.get("game_version", "Unity") == "Unity":
        return UNITY_THEMES.get(str(config.get("unity_theme", "1")), UNITY_THEMES["1"])
    if config.get("game_version", "Unity") == "Wakfu":
        return WAKFU_THEMES.get(str(config.get("wakfu_theme", "1")), WAKFU_THEMES["1"])
    if config.get("game_version") == "Rétro":
        return RETRO_THEMES.get(str(config.get("retro_theme", "1")), RETRO_THEMES["1"])
    return GAME_THEMES.get(config.get("game_version"), GAME_THEMES["Unity"])


def _window_owns_focus(window):
    """True when focus belongs to the window or one of its Tk child popups."""
    try:
        focused = window.focus_get()
        if focused is None:
            return False
        window_path = str(window)
        focused_path = str(focused)
        return focused_path == window_path or focused_path.startswith(window_path + ".")
    except tk.TclError:
        return False


def _pointer_inside_window(window):
    try:
        pointer_x, pointer_y = window.winfo_pointerxy()
        left, top = window.winfo_rootx(), window.winfo_rooty()
        return left <= pointer_x < left + window.winfo_width() and top <= pointer_y < top + window.winfo_height()
    except tk.TclError:
        return False


def close_context_when_clicked_outside(window, close_callback=None):
    """Close a context window after a real click/focus transfer outside it."""
    close_callback = close_callback or window.destroy

    def verify_focus_left(_event=None):
        try:
            if not window.winfo_exists():
                return
            if not _window_owns_focus(window) and not _pointer_inside_window(window):
                close_callback()
        except tk.TclError:
            pass

    window.bind("<FocusOut>", lambda _event: window.after(120, verify_focus_left), add="+")


def close_after_pointer_leaves(window, delay_ms=10_000, close_callback=None):
    """Close a settings window after the pointer remains elsewhere for a while."""
    close_callback = close_callback or window.destroy
    state = {"outside_since": None}

    def poll():
        try:
            if not window.winfo_exists():
                return
            is_inside = _pointer_inside_window(window) or _window_owns_focus(window)
            if is_inside:
                state["outside_since"] = None
            else:
                now = time.monotonic()
                if state["outside_since"] is None:
                    state["outside_since"] = now
                elif (now - state["outside_since"]) * 1000 >= delay_ms:
                    close_callback()
                    return
            window.after(250, poll)
        except tk.TclError:
            pass

    window.after(500, poll)


class CustomObsControlsWindow(ctk.CTkToplevel):
    def _icon_label(self, icon_id):
        default = OBS_ICON_LABELS.get(icon_id, "Icône")
        return ui_text(self.app, f"streamdeck_icon_{icon_id.replace('-', '_')}", default)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner, self.app = owner, owner.app
        self.actions = {
            ui_text(self.app, "streamdeck_action_switch_scene", "Aller à une scène"): "switch_scene",
            ui_text(self.app, "streamdeck_action_toggle_scene", "Scène / retour au second clic"): "toggle_scene",
            ui_text(self.app, "streamdeck_action_toggle_source", "Montrer / cacher une source"): "toggle_source",
            ui_text(self.app, "streamdeck_action_toggle_audio", "Couper / activer une source audio"): "toggle_microphone",
        }
        self.layouts = {
            ui_text(self.app, "streamdeck_layout_horizontal", "Horizontal"): "horizontal",
            ui_text(self.app, "streamdeck_layout_vertical", "Vertical"): "vertical",
            ui_text(self.app, "streamdeck_layout_grid2", "Grille de 2 colonnes"): "grid_2",
            ui_text(self.app, "streamdeck_layout_grid3", "Grille de 3 colonnes"): "grid_3",
        }
        self.title(ui_text(self.app, "streamdeck_title", "Gérer le Streamdeck"))
        self.geometry("650x690")
        self.transient(owner)
        self.attributes("-topmost", True)
        layout_frame = ctk.CTkFrame(self)
        layout_frame.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(layout_frame, text=ui_text(self.app, "streamdeck_layout", "Disposition du Streamdeck")).pack(side="left", padx=8, pady=8)
        current_layout = self.app.obs_bridge.profile.data.get("streamdeck_layout", "horizontal")
        current_label = next((label for label, value in self.layouts.items() if value == current_layout), next(iter(self.layouts)))
        self.layout_box = ctk.CTkComboBox(
            layout_frame, values=list(self.layouts), command=self.save_layout, state="readonly"
        )
        self.layout_box.set(current_label)
        self.layout_box.pack(side="right", padx=8, pady=8)
        size_frame = ctk.CTkFrame(self)
        size_frame.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(size_frame, text=ui_text(self.app, "streamdeck_size", "Taille du Streamdeck")).pack(side="left", padx=(8, 4), pady=8)
        current_scale = max(0.6, min(1.6, float(
            self.app.obs_bridge.profile.data.get("streamdeck_scale", 1.0)
        )))
        self.scale_value = ctk.CTkLabel(size_frame, text=f"{round(current_scale * 100)} %", width=52)
        self.scale_value.pack(side="right", padx=(4, 8), pady=8)
        self.scale_slider = ctk.CTkSlider(
            size_frame, from_=0.6, to=1.6, number_of_steps=20, command=self.save_scale,
        )
        self.scale_slider.set(current_scale)
        self.scale_slider.pack(side="right", fill="x", expand=True, padx=4, pady=8)
        self.list_frame = ctk.CTkScrollableFrame(self, height=240)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=10, pady=(0, 10))
        self.label_entry = ctk.CTkEntry(form, placeholder_text=ui_text(self.app, "streamdeck_button_name", "Nom du bouton"))
        self.label_entry.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.selected_icon_id = DEFAULT_OBS_ICON
        self.icon_images = {}
        icon_panel = ctk.CTkFrame(form)
        icon_panel.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.icon_name = ctk.CTkLabel(icon_panel, text=ui_text(self.app, "streamdeck_icon", "Icône : {name}", name=self._icon_label(DEFAULT_OBS_ICON)), anchor="w")
        self.icon_name.grid(row=0, column=0, columnspan=8, padx=6, pady=(5, 2), sticky="w")
        for index, (icon_id, icon_label) in enumerate(OBS_ICON_CATALOG):
            image = Image.open(obs_icon_path(icon_id))
            self.icon_images[icon_id] = ctk.CTkImage(image, image, size=(24, 24))
            ctk.CTkButton(
                icon_panel, text="", image=self.icon_images[icon_id], width=42, height=38,
                fg_color="#9ebd05" if icon_id == self.selected_icon_id else "#35375c",
                hover_color="#bfdc1c",
                command=lambda value=icon_id: self.select_icon(value),
            ).grid(row=1 + index // 8, column=index % 8, padx=3, pady=3)
        self.icon_buttons = {
            icon_id: widget
            for icon_id, widget in zip(
                (icon_id for icon_id, _label in OBS_ICON_CATALOG),
                [widget for widget in icon_panel.winfo_children() if isinstance(widget, ctk.CTkButton)],
            )
        }
        self.action_box = ctk.CTkComboBox(
            form, values=list(self.actions), command=self._action_changed, state="readonly"
        )
        self.action_box.set(next(iter(self.actions)))
        self.action_box.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        scenes = owner.inventory.get("scenes", []) or [""]
        sources = list(dict.fromkeys(owner.inventory.get("sources", []) + owner.inventory.get("audio_sources", []))) or [""]
        self.scene_box = ctk.CTkComboBox(form, values=scenes, state="readonly")
        self.scene_box.set(scenes[0])
        self.scene_box.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        self.source_box = ctk.CTkComboBox(form, values=sources, state="readonly")
        self.source_box.set(sources[0])
        self.source_box.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(form, text=ui_text(self.app, "streamdeck_add", "Ajouter au dock"), command=self.add_control).grid(
            row=4, column=0, columnspan=2, padx=5, pady=8, sticky="ew"
        )
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        self.refresh_rows()
        self._action_changed(self.action_box.get())

    def _action_changed(self, choice):
        command = self.actions.get(choice)
        self.scene_box.configure(state="readonly" if command in {"switch_scene", "toggle_scene", "toggle_source"} else "disabled")
        self.source_box.configure(state="readonly" if command in {"toggle_source", "toggle_microphone"} else "disabled")

    def select_icon(self, icon_id):
        self.selected_icon_id = icon_id if icon_id in OBS_ICON_LABELS else DEFAULT_OBS_ICON
        self.icon_name.configure(text=ui_text(
            self.app, "streamdeck_icon", "Icône : {name}", name=self._icon_label(self.selected_icon_id)
        ))
        for item_id, button in self.icon_buttons.items():
            button.configure(fg_color="#9ebd05" if item_id == self.selected_icon_id else "#35375c")

    def refresh_rows(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        controls = ordered_streamdeck_controls(self.app.obs_bridge.profile.data)
        if not controls:
            ctk.CTkLabel(self.list_frame, text=ui_text(self.app, "streamdeck_empty", "Aucun bouton dans le Streamdeck.")).pack(pady=20)
            return
        for control in controls:
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=3)
            icon_id = control.get("icon_id", DEFAULT_OBS_ICON)
            icon_label = self._icon_label(icon_id)
            kind = ui_text(self.app, "streamdeck_builtin", "Prédéfini") if control.get("builtin") else ui_text(self.app, "streamdeck_custom", "Personnalisé")
            description = ui_text(
                self.app, "streamdeck_row_description", "{icon} · {label} — {kind}",
                icon=icon_label, label=control.get("label", "Bouton"), kind=kind,
            )
            ctk.CTkLabel(row, text=description, anchor="w").pack(side="left", fill="x", expand=True, padx=8)
            ctk.CTkButton(row, text=ui_text(self.app, "streamdeck_delete", "Supprimer"), width=85, fg_color="#9b3d1f",
                          command=lambda value=control["id"]: self.remove_control(value)).pack(side="right", padx=5, pady=5)
            ctk.CTkButton(row, text="↓", width=30,
                          command=lambda value=control["id"]: self.move_control(value, 1)).pack(side="right", padx=2)
            ctk.CTkButton(row, text="↑", width=30,
                          command=lambda value=control["id"]: self.move_control(value, -1)).pack(side="right", padx=2)

    def save_layout(self, choice):
        self.app.obs_bridge.profile.data["streamdeck_layout"] = self.layouts.get(choice, "horizontal")
        self.app.obs_bridge.profile.save()
        self.app.refresh_obs_stream_dock()

    def save_scale(self, value):
        scale = round(max(0.6, min(1.6, float(value))) * 20) / 20
        self.scale_value.configure(text=f"{round(scale * 100)} %")
        if self.app.obs_bridge.profile.data.get("streamdeck_scale") == scale:
            return
        self.app.obs_bridge.profile.data["streamdeck_scale"] = scale
        self.app.obs_bridge.profile.save()
        self.app.refresh_obs_stream_dock()

    def add_control(self):
        choice = self.action_box.get()
        command = self.actions.get(choice)
        label = self.label_entry.get().strip() or "OBS"
        control = {
            "id": f"custom-{int(time.time() * 1000)}",
            "label": label,
            "icon_id": self.selected_icon_id,
            "command": command,
            "scene": self.scene_box.get().strip() if command in {"switch_scene", "toggle_scene", "toggle_source"} else "",
            "source": self.source_box.get().strip() if command in {"toggle_source", "toggle_microphone"} else "",
        }
        self.app.obs_bridge.profile.data.setdefault("custom_controls", []).append(control)
        self.app.obs_bridge.profile.data.setdefault("streamdeck_order", []).append(control["id"])
        self.app.obs_bridge.profile.save()
        self.app.refresh_obs_stream_dock()
        self.refresh_rows()

    def remove_control(self, control_id):
        remove_streamdeck_control(self.app.obs_bridge.profile.data, control_id)
        self.app.obs_bridge.profile.data.setdefault("dock_states", {}).pop(str(control_id), None)
        self.app.obs_bridge.profile.save()
        self.app.refresh_obs_stream_dock()
        self.refresh_rows()

    def move_control(self, control_id, direction):
        if move_streamdeck_control(self.app.obs_bridge.profile.data, control_id, direction):
            self.app.obs_bridge.profile.save()
            self.app.refresh_obs_stream_dock()
            self.refresh_rows()


class ObsSettingsWindow(ctk.CTkToplevel):
    """Guided OBS extension setup, visible only after explicit activation."""
    def __init__(self, settings):
        parent_window = settings if isinstance(settings, tk.Misc) else settings.root
        super().__init__(parent_window)
        self.settings, self.app = settings, settings.app
        self.title(ui_text(self.app, "obs_assistant_window_title", "OBS — DOSOFT"))
        self.geometry("560x700")
        self.minsize(520, 600)
        self.transient(parent_window)
        self.attributes("-topmost", True)
        profile = self.app.obs_bridge.profile.data
        self.game_scene_key = self.app.obs_bridge.active_game_scene_key()
        self.auto = ctk.BooleanVar(value=self.app.config.data.get("obs_auto_swap_enabled", False))
        self.dock = ctk.BooleanVar(value=profile.get("dock_enabled", False))
        self.fallback = ctk.BooleanVar(value=profile.get("fallback_enabled", False))
        self.diagnostics = ctk.BooleanVar(value=profile.get("diagnostics_enabled", False))
        self.inventory = {"scenes": [], "sources": [], "audio_sources": []}
        self._obs_responses = queue.Queue()
        self._last_connection_state = None

        status_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color="#9ebd05")
        status_frame.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        self.status = ctk.CTkLabel(
            status_frame, text=self.app.obs_bridge.last_status, wraplength=450, justify="center",
            anchor="center", font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.status.pack(fill="x", padx=10, pady=10)
        body = ctk.CTkScrollableFrame(self)
        body.pack(side="top", fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(body, text=ui_text(self.app, "obs_assistant_title", "Assistant OBS"), font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=8, pady=(4, 2))
        guide = ctk.CTkFrame(body, corner_radius=12, border_width=1, border_color="#35375c")
        guide.pack(fill="x", padx=8, pady=(4, 10))
        ctk.CTkLabel(
            guide,
            text=ui_text(self.app, "obs_assistant_steps", "1. Détecter OBS   ·   2. Relier la scène   ·   3. Synchroniser"),
            font=ctk.CTkFont(weight="bold"), wraplength=450, justify="center",
        ).pack(padx=10, pady=(8, 2))
        ctk.CTkLabel(
            guide, text=ui_text(self.app, "obs_assistant_help", "Gardez OBS ouvert et lancez au moins une fenêtre Dofus."),
            wraplength=450, justify="center",
        ).pack(padx=10, pady=(0, 8))
        ctk.CTkButton(body, text=ui_text(self.app, "obs_step_detect", "1. Détecter OBS et ses scènes"), command=self.detect_obs).pack(fill="x", padx=8, pady=4)

        self.entries = {}
        for key, label in (("stream_scene", ui_text(self.app, "obs_label_stream_scene", "Scène principale / retour")),
                           ("game_scene", ui_text(self.app, "obs_label_game_scene", "Scène Dofus gérée par DOSOFT")),
                           ("fallback_scene", ui_text(self.app, "obs_label_fallback_scene", "Scène de secours")),
                           ("pause_scene", ui_text(self.app, "obs_label_pause_scene", "Scène pause")),
                           ("microphone_source", ui_text(self.app, "obs_label_microphone_source", "Source micro")),
                           ("camera_scene", ui_text(self.app, "obs_label_camera_scene", "Scène contenant la caméra")),
                           ("camera_source", ui_text(self.app, "obs_label_camera_source", "Source caméra"))):
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=3)
            ctk.CTkLabel(row, text=label, width=230, anchor="w").pack(side="left")
            entry = ctk.CTkComboBox(
                row, width=220,
                values=[str(self.app.obs_bridge.active_game_scene() if key == "game_scene" else profile.get(key, ""))],
                state="readonly"
            )
            entry.set(str(self.app.obs_bridge.active_game_scene() if key == "game_scene" else profile.get(key, "")))
            entry.pack(side="right")
            self.entries[key] = entry

        ctk.CTkSwitch(body, text=ui_text(self.app, "obs_switch_autoswap", "Auto-swap des clients Dofus"), variable=self.auto).pack(anchor="w", padx=8, pady=(10, 3))
        ctk.CTkSwitch(body, text=ui_text(self.app, "obs_switch_fallback", "Utiliser une scène de secours"), variable=self.fallback).pack(anchor="w", padx=8, pady=3)
        self.streamdeck_switch = ctk.CTkSwitch(
            body,
            text=ui_text(self.app, "obs_switch_streamdeck", "Afficher le Streamdeck"),
            variable=self.dock,
            command=self.toggle_streamdeck_immediately,
        )
        self.streamdeck_switch.pack(anchor="w", padx=8, pady=3)
        ctk.CTkSwitch(body, text=ui_text(self.app, "obs_switch_diagnostics", "Activer les journaux de diagnostic"), variable=self.diagnostics).pack(anchor="w", padx=8, pady=3)

        ctk.CTkButton(body, text=ui_text(self.app, "obs_step_link", "2. Créer et relier la scène Dofus"), command=self.apply_setup).pack(fill="x", padx=8, pady=(14, 4))
        ctk.CTkButton(body, text=ui_text(self.app, "obs_step_sync", "3. Synchroniser les personnages détectés"), command=lambda: self.action("sync")).pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(body, text=ui_text(self.app, "obs_manage_streamdeck", "Gérer le Streamdeck"),
                      command=self.open_custom_controls).pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(body, text=ui_text(self.app, "obs_rebuild_captures", "Reconstruire uniquement les captures DOSOFT"), fg_color="#9b3d1f",
                      command=lambda: self.action("rebuild")).pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(body, text=ui_text(self.app, "obs_save_choices", "Enregistrer ces choix sur cet ordinateur"), command=self.save).pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(body, text=ui_text(self.app, "obs_save_help", "Ce bouton mémorise les choix localement, sans créer ni supprimer de source OBS."),
                     wraplength=450, justify="center").pack(padx=8, pady=(0, 8))

        self.after(120, self.detect_obs)
        self.after(100, self._poll_obs_responses)
        self.after(150, self._poll_connection_state)
        self.after(20, self.show_foreground)

    def _poll_connection_state(self):
        snapshot = self.app.obs_bridge.status_snapshot()
        state = snapshot["state"]
        signature = (
            state, snapshot.get("plugin_version"), snapshot.get("obs_version"),
            tuple(snapshot.get("compatibility_warnings", [])),
        )
        if signature != self._last_connection_state:
            if state == "connected":
                warnings = snapshot.get("compatibility_warnings", [])
                if warnings:
                    self.status.configure(text="⚠ " + " ".join(warnings))
                else:
                    self.status.configure(text=ui_text(
                        self.app, "obs_connected_ready", "OBS {obs_version} connecté — plugin {plugin_version} prêt.",
                        obs_version=snapshot.get("obs_version") or "?",
                        plugin_version=snapshot.get("plugin_version") or "?",
                    ))
            elif state in {"disconnected", "degraded", "incompatible", "profile_required"}:
                self.status.configure(text=snapshot["message"])
            self._last_connection_state = signature
        try:
            self.after(500, self._poll_connection_state)
        except tk.TclError:
            pass

    def show_foreground(self):
        """Use a tall normal window and keep it above the separate Settings window."""
        try:
            self.deiconify()
            self.state("normal")
            self.update_idletasks()
            width = 560
            height = max(600, min(880, self.winfo_screenheight() - 100))
            left = max(0, (self.winfo_screenwidth() - width) // 2)
            top = max(20, (self.winfo_screenheight() - height) // 2)
            self.geometry(f"{width}x{height}+{left}+{top}")
            self.attributes("-topmost", True)
            self.lift()
            self.focus_force()
            # Windows can briefly reactivate the previously focused topmost window.
            self.after(180, self._confirm_foreground)
        except tk.TclError:
            pass

    def _confirm_foreground(self):
        try:
            self.attributes("-topmost", True)
            self.lift()
            self.focus_force()
        except tk.TclError:
            pass

    def _on_ui(self, callback):
        def wrapped(value):
            self._obs_responses.put((callback, value))
        return wrapped

    def _poll_obs_responses(self):
        try:
            while True:
                callback, value = self._obs_responses.get_nowait()
                callback(value)
        except queue.Empty:
            pass
        try:
            self.after(100, self._poll_obs_responses)
        except tk.TclError:
            pass

    def detect_obs(self):
        self.status.configure(text=ui_text(self.app, "obs_detecting", "Recherche d'OBS, du plugin et des trois scènes de jeu…"))
        self.app.obs_bridge.query_inventory(self._on_ui(self._inventory_received))

    def _inventory_received(self, response):
        if not response.get("ok"):
            if is_process_running("obs64.exe"):
                self.status.configure(text=ui_text(
                    self.app, "obs_running_plugin_missing",
                    "OBS est ouvert, mais le connecteur DOSOFT ne répond pas. Fermez puis relancez OBS. Si le problème continue, réinstallez le connecteur OBS."
                ))
            else:
                self.status.configure(text=ui_text(
                    self.app, "obs_closed", "OBS Studio est fermé. Ouvrez OBS, attendez son chargement puis relancez l’étape 1."
                ))
            return
        inventory = response.get("data") or self.inventory
        scenes = inventory.get("scenes", [])
        expected = self.app.obs_bridge.expected_game_scenes()
        missing = [scene for scene in expected if scene not in scenes]
        if missing:
            self.status.configure(text=ui_text(
                self.app, "obs_creating_missing_scenes", "OBS connecté. Création des scènes manquantes : {scenes}…",
                scenes=", ".join(missing),
            ))
            self.app.obs_bridge.ensure_all_game_scenes(
                missing, self._on_ui(self._game_scenes_created)
            )
            return
        self._apply_inventory(response, [])

    def _game_scenes_created(self, response):
        if not response.get("ok"):
            failed = (response.get("data") or {}).get("failed_scene", "une scène de jeu")
            self.status.configure(text=ui_text(
                self.app, "obs_failed_create_scene",
                "OBS est détecté, mais la création de {scene} a échoué. Vérifiez le plugin puis réessayez.", scene=failed,
            ))
            return
        created = (response.get("data") or {}).get("created_scenes", [])
        self.status.configure(text=ui_text(self.app, "obs_created_verify", "Scènes créées. Vérification de l'inventaire OBS…"))
        self.app.obs_bridge.query_inventory(
            self._on_ui(lambda inventory: self._verified_inventory_received(inventory, created))
        )

    def _verified_inventory_received(self, response, created):
        if not response.get("ok"):
            self.status.configure(text=ui_text(
                self.app, "obs_inventory_after_create_failed",
                "Les scènes ont été créées, mais OBS n'a pas renvoyé son inventaire final. Relancez la détection."
            ))
            return
        inventory = response.get("data") or self.inventory
        scenes = inventory.get("scenes", [])
        missing = [
            scene for scene in self.app.obs_bridge.expected_game_scenes()
            if scene not in scenes
        ]
        if missing:
            self.status.configure(text=ui_text(
                self.app, "obs_setup_missing_scenes", "Configuration incomplète. Scènes encore absentes : {scenes}.",
                scenes=", ".join(missing),
            ))
            return
        self._apply_inventory(response, created)

    def _apply_inventory(self, response, created):
        self.inventory = response.get("data") or self.inventory
        scenes = sorted(self.inventory.get("scenes", []), key=str.casefold)
        sources = sorted(self.inventory.get("sources", []), key=str.casefold)
        audio = sorted(self.inventory.get("audio_sources", []), key=str.casefold)
        for key in ("stream_scene", "game_scene", "fallback_scene", "pause_scene", "camera_scene"):
            current = self.entries[key].get()
            self.entries[key].configure(values=list(dict.fromkeys(([current] if current else []) + scenes)))
        for key in ("camera_source",):
            current = self.entries[key].get()
            self.entries[key].configure(values=list(dict.fromkeys(([current] if current else []) + sources)))
        current = self.entries["microphone_source"].get()
        self.entries["microphone_source"].configure(values=list(dict.fromkeys(([current] if current else []) + audio)))
        if created:
            self.status.configure(text=ui_text(
                self.app, "obs_created_scenes", "OBS connecté. Scènes créées automatiquement : {scenes}.",
                scenes=", ".join(created),
            ))
        else:
            self.status.configure(text=ui_text(
                self.app, "obs_inventory_ready", "OBS connecté : {count} scène(s) détectée(s). Les trois scènes de jeu sont prêtes.",
                count=len(scenes),
            ))

    def save(self):
        profile = self.app.obs_bridge.profile.data
        for key, entry in self.entries.items():
            destination_key = self.game_scene_key if key == "game_scene" else key
            profile[destination_key] = entry.get().strip()
        profile["parent_scenes"] = [profile["stream_scene"]] if profile["stream_scene"] else []
        profile["fallback_enabled"] = self.fallback.get()
        profile["dock_enabled"] = self.dock.get()
        profile["diagnostics_enabled"] = self.diagnostics.get()
        if not self.app.obs_bridge.profile.save():
            self.status.configure(text=self.app.obs_bridge.profile.last_error)
            return False
        self.app.obs_bridge.set_auto_swap(self.auto.get())
        self.app.refresh_obs_stream_dock()
        try:
            saved = json.loads(self.app.obs_bridge.profile.path.read_text(encoding="utf-8"))
            if saved.get("version") != PROFILE_VERSION:
                raise ValueError("version locale invalide")
            self.status.configure(text=ui_text(
                self.app, "obs_saved_local", "Choix enregistrés localement dans : {path}",
                path=self.app.obs_bridge.profile.path,
            ))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self.status.configure(text=ui_text(
                self.app, "obs_save_failed", "Échec de l'enregistrement local : {error}", error=error,
            ))
            return False
        return True

    def toggle_streamdeck_immediately(self):
        """Persist and apply the dock switch without waiting for the form save.

        The Streamdeck is an independent optional window. Requiring the user to
        click the profile save button after enabling it made the switch appear
        broken and left no persistent state after closing the assistant.
        """
        enabled = bool(self.dock.get())
        profile = self.app.obs_bridge.profile
        previous = bool(profile.data.get("dock_enabled", False))
        profile.data["dock_enabled"] = enabled
        if not profile.save():
            profile.data["dock_enabled"] = previous
            self.dock.set(previous)
            self.status.configure(text=profile.last_error)
            return False
        self.app.refresh_obs_stream_dock()
        self.status.configure(text=ui_text(
            self.app,
            "obs_streamdeck_enabled" if enabled else "obs_streamdeck_disabled",
            "Streamdeck activé et enregistré localement."
            if enabled else "Streamdeck désactivé et enregistré localement.",
        ))
        return True

    def apply_setup(self):
        if not self.save():
            return
        parents = self.app.obs_bridge.profile.data.get("parent_scenes", [])
        self.status.configure(text=ui_text(self.app, "obs_linking_scene", "Création et liaison de la scène Dofus…"))
        self.app.obs_bridge.setup_scenes(parents, self._on_ui(self._setup_received))

    def _setup_received(self, response):
        if response.get("ok"):
            game_scene = self.app.obs_bridge.active_game_scene()
            self.status.configure(text=ui_text(
                self.app, "obs_setup_congratulations",
                "Félicitations, la connexion est réussie ! Vous avez une nouvelle source dans votre scène de stream nommée : {scene}.",
                scene=game_scene,
            ))
        else:
            self.status.configure(text=ui_text(
                self.app, "obs_setup_incomplete", "Configuration incomplète : vérifiez la scène principale sélectionnée."
            ))

    def open_custom_controls(self):
        if not hasattr(self, "custom_controls_window") or not self.custom_controls_window.winfo_exists():
            self.custom_controls_window = CustomObsControlsWindow(self)
        else:
            self.custom_controls_window.lift()
            self.custom_controls_window.focus_force()

    def action(self, name):
        self.save()
        self.status.configure(text=ui_text(self.app, "obs_sync_preparing", "Actualisation de DOSOFT et préparation des captures OBS…"))
        callback = self._on_ui(lambda response: self._sync_received(name, response))
        if name == "sync":
            self.app.sync_obs_team(callback)
        else:
            self.app.rebuild_obs_team(callback)

    def _sync_received(self, name, response):
        if response.get("ok"):
            if name == "rebuild":
                self.status.configure(text=ui_text(self.app, "obs_rebuild_success", "Redémarrage d'urgence réussi : les captures DOSOFT ont été recréées dans OBS."))
            else:
                self.status.configure(text=ui_text(self.app, "obs_sync_success", "Synchronisation réussie : les personnages détectés sont maintenant prêts dans OBS."))
        elif response.get("error") == "no_ready_accounts":
            self.status.configure(text=ui_text(self.app, "obs_no_ready_accounts", "Aucun personnage Dofus prêt. Ouvrez une page Dofus puis recommencez l'étape 3."))
        else:
            self.status.configure(text=self.app.obs_bridge._error_message(name, response.get("error")))

class RetroAutofocusSettingsWindow(ctk.CTkToplevel):
    """Instant, language-neutral filters for actionable Retro notifications."""

    EVENT_DEFINITIONS = (
        ("combat", "retro_event_combat", "Tour de combat"),
        ("private_message", "retro_event_private_message", "Message privé"),
        ("trade", "retro_event_trade", "Demande d’échange"),
        ("group", "retro_event_group", "Invitation groupe / guilde"),
        ("challenge", "retro_event_challenge", "Défi"),
        ("craft", "retro_event_craft", "Atelier / artisanat"),
        ("pvp", "retro_event_pvp", "Attaque de percepteur"),
    )

    def __init__(self, owner):
        super().__init__(owner.root)
        self.owner, self.app = owner, owner.app
        self.title(self.app.i18n.t("retro_autofocus_settings_title", "Réglages Auto-Focus Rétro"))
        self.geometry("440x330")
        self.resizable(False, False)
        self.transient(owner.root)
        self.attributes("-topmost", True)

        theme = owner.game_theme
        self.configure(fg_color=theme["background"])
        ctk.CTkLabel(
            self,
            text=self.app.i18n.t("retro_autofocus_settings_title", "Réglages Auto-Focus Rétro"),
            font=ctk.CTkFont(size=17, weight="bold"), text_color=theme["title"],
        ).pack(anchor="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(
            self,
            text=self.app.i18n.t(
                "retro_autofocus_settings_help",
                "Choisissez les notifications qui peuvent mettre une fenêtre au premier plan. "
                "Les filtres reconnaissent automatiquement la langue du jeu.",
            ),
            justify="left", wraplength=400, text_color=theme["muted"], font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=18, pady=(0, 8))

        enabled = set(self.app.config.data.get("retro_autofocus_events", []))
        self.variables = {}
        list_frame = ctk.CTkFrame(
            self, corner_radius=12, fg_color=theme["panel"], border_width=1,
            border_color=theme["border"],
        )
        list_frame.pack(fill="x", padx=16, pady=(0, 8))
        for column in range(2):
            list_frame.grid_columnconfigure(column, weight=1, uniform="retro_event")
        for index, (event_id, label_key, fallback) in enumerate(self.EVENT_DEFINITIONS):
            variable = ctk.BooleanVar(value=event_id in enabled)
            self.variables[event_id] = variable
            checkbox = ctk.CTkCheckBox(
                list_frame,
                text=self.app.i18n.t(label_key, fallback),
                variable=variable,
                command=self.save_selection,
                width=180, height=28, checkbox_width=19, checkbox_height=19,
                corner_radius=5, border_width=2,
                fg_color=theme["accent"], hover_color=theme["accent_hover"],
                border_color=theme["border"], text_color=theme["title"],
                font=ctk.CTkFont(size=12),
            )
            checkbox.grid(row=index // 2, column=index % 2, sticky="w", padx=12, pady=6)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkButton(
            actions, text=self.app.i18n.t("select_all", "Tout"), width=74, height=27,
            fg_color=theme["panel_alt"], hover_color=theme["accent_hover"],
            command=lambda: self.set_all(True),
        ).pack(side="left")
        ctk.CTkButton(
            actions, text=self.app.i18n.t("select_none", "Aucun"), width=74, height=27,
            fg_color=theme["panel_alt"], hover_color=theme["accent_hover"],
            command=lambda: self.set_all(False),
        ).pack(side="left", padx=6)

        self.status = ctk.CTkLabel(
            actions, text="", text_color=theme["muted"], font=ctk.CTkFont(size=12),
        )
        self.status.pack(side="right", padx=4)
        self.update_status()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(50, self._bring_to_front)
        close_context_when_clicked_outside(self, self.close)

    def _bring_to_front(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def save_selection(self):
        enabled = [
            event_id for event_id, _label_key, _fallback in self.EVENT_DEFINITIONS
            if self.variables[event_id].get()
        ]
        self.app.update_retro_autofocus_events(enabled)
        self.update_status()

    def set_all(self, enabled):
        for variable in self.variables.values():
            variable.set(enabled)
        self.save_selection()

    def update_status(self):
        active = sum(variable.get() for variable in self.variables.values())
        self.status.configure(
            text=self.app.i18n.t(
                "retro_autofocus_settings_status", "{active}/{total} types de notification actifs"
            ).format(active=active, total=len(self.variables))
        )

    def close(self):
        self.owner.retro_autofocus_settings_window = None
        self.destroy()


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent_gui):
        super().__init__(parent_gui.root)
        self.parent = parent_gui
        self.app = parent_gui.app
        self.title(self.app.i18n.t("settings_title", "⚙️ Paramètres"))
        self.geometry("450x500")
        self.minsize(350, 300)
        self.attributes("-topmost", True)
        self.bind("<Unmap>", self.close_when_minimized, add="+")
        self.resizable(True, True)

        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True, padx=5, pady=5)
        theme = parent_gui.game_theme
        is_module_theme = self.app.config.data.get("game_version") in ("Unity", "Wakfu", "Rétro")
        input_color = theme["accent"] if is_module_theme else "#3a7ebf"
        input_hover = theme["accent_hover"] if is_module_theme else "#1f538d"
        clear_color = theme.get("clear", "#c0392b") if is_module_theme else "#c0392b"
        clear_hover = theme.get("clear_hover", "#e74c3c") if is_module_theme else "#e74c3c"
        self.theme_selector_buttons = {}

        title_font = ctk.CTkFont(size=16, weight="bold")

        # This module stays at the very top because it protects settings that
        # Dofus can silently overwrite. All disk work runs outside Tk's thread.
        self._dofus_display_results = queue.Queue()
        self._dofus_display_busy = False
        self.dofus_display_buttons = []
        self.lbl_dofus_display_title = ctk.CTkLabel(
            self.scroll_container, text=ui_text(self.app, "dofus_display_title", "Affichage Dofus"), font=title_font,
        )
        self.lbl_dofus_display_title.pack(pady=(8, 5))
        self.frame_dofus_display = ctk.CTkFrame(
            self.scroll_container, corner_radius=12, border_width=1,
            border_color=theme["border"],
        )
        self.frame_dofus_display.pack(fill="x", padx=10, pady=(0, 10))
        self.lbl_dofus_display_help = ctk.CTkLabel(
            self.frame_dofus_display,
            text=ui_text(
                self.app, "dofus_display_help",
                "Préparez votre interface parfaite dans Dofus, fermez ce compte en dernier, puis enregistrez JEU CLASSIQUE. Fermez tous les clients avant chaque opération.",
            ),
            wraplength=390, justify="left", anchor="w",
        )
        self.lbl_dofus_display_help.pack(fill="x", padx=10, pady=(10, 6))
        self.lbl_dofus_display_status = ctk.CTkLabel(
            self.frame_dofus_display, text=ui_text(self.app, "dofus_display_loading", "Lecture des réglages Dofus…"),
            wraplength=390, justify="left", anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.lbl_dofus_display_status.pack(fill="x", padx=10, pady=(0, 8))
        dofus_actions = ctk.CTkFrame(self.frame_dofus_display, fg_color="transparent")
        dofus_actions.pack(fill="x", padx=7, pady=(0, 9))
        for column in range(2):
            dofus_actions.grid_columnconfigure(column, weight=1)
        self.dofus_display_button_keys = []
        for key, text, command, row, column, destructive in (
            ("dofus_display_capture", "Enregistrer JEU CLASSIQUE", self.capture_dofus_display_profile, 0, 0, False),
            ("dofus_display_apply", "Appliquer aux comptes", self.apply_dofus_display_profile, 0, 1, False),
            ("dofus_display_backup", "Sauvegarder maintenant", self.backup_dofus_display, 1, 0, False),
            ("dofus_display_restore", "Restaurer la dernière", self.restore_dofus_display, 1, 1, True),
        ):
            button = ctk.CTkButton(
                dofus_actions, text=ui_text(self.app, key, text), command=command,
                fg_color=clear_color if destructive else input_color,
                hover_color=clear_hover if destructive else input_hover,
            )
            button.grid(row=row, column=column, padx=3, pady=3, sticky="ew")
            self.dofus_display_buttons.append(button)
            self.dofus_display_button_keys.append((button, key, text))
        self.after(80, self._poll_dofus_display_results)
        self.after(120, self.refresh_dofus_display_status)

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
        btn_hk = ctk.CTkButton(frame_hk, text=current_val if current_val else self.app.i18n.t("none", "Aucun"), width=120, fg_color=input_color, hover_color=input_hover, command=lambda: self.parent.catch_key("radial_menu_hotkey", btn_hk, allow_mouse=True))
        btn_hk.pack(side="left", padx=5)
        self.btn_radial_hotkey = btn_hk
        self.parent.hotkey_btns["radial_menu_hotkey"] = self.btn_radial_hotkey

        btn_x = ctk.CTkButton(frame_hk, text="✖", width=25, fg_color=clear_color, hover_color=clear_hover, command=lambda: self.parent.clear_key("radial_menu_hotkey", btn_hk))
        btn_x.pack(side="left", padx=5)

        # Fast Switch TEAM only controls the translucent companion bar; the
        # normal Team 1 / Team 2 selector always remains available.
        self.frame_fast_switch_team = ctk.CTkFrame(self.scroll_container)
        self.lbl_fast_switch_team = ctk.CTkLabel(self.frame_fast_switch_team, text=ui_text(self.app, "settings_fast_switch", "Fast Switch TEAM"))
        self.lbl_fast_switch_team.pack(side="left", padx=8, pady=8)
        self.var_fast_switch_team_disabled = ctk.BooleanVar(
            value=True
        )
        self.sw_fast_switch_team_disabled = ctk.CTkSwitch(
            self.frame_fast_switch_team,
            text=ui_text(self.app, "disable", "Désactiver"),
            variable=self.var_fast_switch_team_disabled,
            command=self.on_fast_switch_team_change,
            width=96,
        )
        self.sw_fast_switch_team_disabled.pack(side="right", padx=(3, 8), pady=8)

        self.frame_hotkey_overlap = ctk.CTkFrame(self.scroll_container)
        self.frame_hotkey_overlap.pack(fill="x", padx=10, pady=5)
        self.lbl_hotkey_overlap = ctk.CTkLabel(
            self.frame_hotkey_overlap,
            text=ui_text(self.app, "settings_hotkey_overlap", "Superposer les raccourcis"),
        )
        self.lbl_hotkey_overlap.pack(side="left", padx=8, pady=8)
        self.var_hotkey_overlap = ctk.BooleanVar(
            value=self.app.config.data.get("hotkey_chord_overlap_enabled", False)
        )
        self.sw_hotkey_overlap = ctk.CTkSwitch(
            self.frame_hotkey_overlap,
            text=ui_text(self.app, "enable", "Activer"),
            variable=self.var_hotkey_overlap,
            command=self.on_hotkey_overlap_change,
            width=90,
        )
        self.sw_hotkey_overlap.pack(side="right", padx=8, pady=8)

        self.frame_team_switch_hotkey = ctk.CTkFrame(self.scroll_container)
        self.lbl_team_switch_hotkey = ctk.CTkLabel(
            self.frame_team_switch_hotkey, text=ui_text(self.app, "settings_team_switch_hotkey", "Raccourci switch de mode TEAM")
        )
        self.lbl_team_switch_hotkey.pack(side="left", padx=8, pady=8)
        current_team_switch_hotkey = self.app.config.data.get("team_switch_key", "")
        self.btn_team_switch_hotkey = ctk.CTkButton(
            self.frame_team_switch_hotkey,
            text=current_team_switch_hotkey or self.app.i18n.t("none", "Aucun"),
            width=100, fg_color=input_color, hover_color=input_hover,
            command=lambda: self.parent.catch_key("team_switch_key", self.btn_team_switch_hotkey),
        )
        self.btn_team_switch_hotkey.pack(side="right", padx=(3, 8), pady=8)
        self.parent.hotkey_btns["team_switch_key"] = self.btn_team_switch_hotkey
        self.btn_team_switch_clear = ctk.CTkButton(
            self.frame_team_switch_hotkey, text="✖", width=25,
            fg_color=clear_color, hover_color=clear_hover,
            command=lambda: self.parent.clear_key("team_switch_key", self.btn_team_switch_hotkey),
        )
        self.btn_team_switch_clear.pack(side="right", padx=3, pady=8)
        self.parent.hotkey_clear_buttons.append(self.btn_team_switch_clear)

        self.frame_character_bar_format = ctk.CTkFrame(self.scroll_container)
        self.frame_character_bar_format.pack(fill="x", padx=10, pady=5)
        self.lbl_character_bar_format = ctk.CTkLabel(
            self.frame_character_bar_format, text=ui_text(self.app, "settings_compact_character_bar", "Barre perso minimale")
        )
        self.lbl_character_bar_format.pack(side="left", padx=8, pady=8)
        self.var_character_bar_compact = ctk.BooleanVar(
            value=self.app.config.data.get("character_bar_compact", False)
        )
        self.sw_character_bar_compact = ctk.CTkSwitch(
            self.frame_character_bar_format,
            text=ui_text(self.app, "enable", "Activer"),
            variable=self.var_character_bar_compact,
            command=self.on_character_bar_compact_change,
            width=90,
        )
        self.sw_character_bar_compact.pack(side="right", padx=8, pady=8)

        self.var_wakfu_theme = ctk.StringVar(value=str(self.app.config.data.get("wakfu_theme", "1")))
        self.var_unity_theme = ctk.StringVar(value=str(self.app.config.data.get("unity_theme", "1")))
        self.var_retro_theme = ctk.StringVar(value=str(self.app.config.data.get("retro_theme", "1")))
        self.frame_wakfu_theme, self.lbl_wakfu_theme = self.create_theme_selector(
            "WAKFU", self.var_wakfu_theme, WAKFU_THEMES, self.on_wakfu_theme_change
        )
        self.frame_unity_theme, self.lbl_unity_theme = self.create_theme_selector(
            "UNITY", self.var_unity_theme, UNITY_THEMES, self.on_unity_theme_change
        )
        self.frame_retro_theme, self.lbl_retro_theme = self.create_theme_selector(
            "Rétro", self.var_retro_theme, RETRO_THEMES, self.on_retro_theme_change
        )

        frame_language = ctk.CTkFrame(self.scroll_container)
        frame_language.pack(fill="x", padx=10, pady=5)
        self.lbl_language = ctk.CTkLabel(frame_language, text=self.app.i18n.t("settings_language", "Langue"))
        self.lbl_language.pack(side="left", padx=8, pady=8)
        current_locale = self.app.config.data.get("language", "fr")
        self.var_language = ctk.StringVar(value=LANGUAGE_NAMES.get(current_locale, LANGUAGE_NAMES["fr"]))
        self.language_menu = ctk.CTkOptionMenu(
            frame_language, values=list(LANGUAGE_NAMES.values()), variable=self.var_language,
            command=lambda _: self.save_settings(),
        )
        self.language_menu.pack(side="right", padx=8, pady=8)

        frame_keyboard = ctk.CTkFrame(self.scroll_container)
        frame_keyboard.pack(fill="x", padx=10, pady=5)
        self.lbl_keyboard = ctk.CTkLabel(frame_keyboard, text=self.app.i18n.t("settings_keyboard_layout", "Disposition clavier"))
        self.lbl_keyboard.pack(side="left", padx=8, pady=8)
        self.var_keyboard_layout = ctk.StringVar(value=self.app.config.data.get("keyboard_layout", "azerty_fr"))
        ctk.CTkOptionMenu(frame_keyboard, values=["azerty_fr", "qwerty_us"], variable=self.var_keyboard_layout, command=lambda _: self.save_settings()).pack(side="right", padx=8, pady=8)
        
        # --- BLOC MOTEUR NOTIFICATIONS (DEBUG) ---
        frame_debug = ctk.CTkFrame(self.scroll_container)
        frame_debug.pack(fill="x", padx=10, pady=5)
        
        self.lbl_debug = ctk.CTkLabel(frame_debug, text=ui_text(self.app, "settings_autofocus_engine", "Moteur Auto-Focus (dépannage)"))
        self.lbl_debug.pack(side="left", padx=8, pady=8)
        
        # On définit v2 par défaut
        self.notification_mode_labels = {
            ui_text(self.app, "notification_mode_automatic", "Automatique"): "Automatique",
            ui_text(self.app, "notification_mode_polling", "Polling"): "Polling",
        }
        saved_notification_mode = str(self.app.config.data.get("notif_api_mode", "Automatique"))
        if saved_notification_mode not in {"Automatique", "Polling"}:
            saved_notification_mode = "Automatique"
        saved_notification_label = next(
            (label for label, value in self.notification_mode_labels.items() if value == saved_notification_mode),
            next(iter(self.notification_mode_labels)),
        )
        self.var_notif_api = ctk.StringVar(value=saved_notification_label)
        
        # Le sélecteur avec les 3 versions
        self.combo_debug = ctk.CTkOptionMenu(
            frame_debug, 
            values=list(self.notification_mode_labels),
            variable=self.var_notif_api, 
            command=self.on_notif_api_change
        )
        self.combo_debug.pack(side="right", padx=8, pady=8)
        self.parent.bind_i18n_tooltip(
            self.combo_debug, "tooltip_api_mode",
            "Automatique écoute les événements Windows avec un polling de secours. "
            "Polling sert uniquement au dépannage. Nécessite un redémarrage.",
        )

        frame_retro_log = ctk.CTkFrame(self.scroll_container)
        frame_retro_log.pack(fill="x", padx=10, pady=5)
        self.lbl_retro_log = ctk.CTkLabel(frame_retro_log, text=ui_text(self.app, "settings_retro_diagnostic", "Diagnostic Auto-Focus Rétro"))
        self.lbl_retro_log.pack(side="left", padx=8, pady=8)
        self.btn_retro_log = ctk.CTkButton(
            frame_retro_log, text=ui_text(self.app, "settings_open_log", "Ouvrir le journal"), width=132,
            command=self.open_retro_autofocus_log,
        )
        self.btn_retro_log.pack(side="right", padx=8, pady=8)

        self.frame_obs = ctk.CTkFrame(self.scroll_container)
        self.frame_obs.pack(fill="x", padx=10, pady=(18, 5))
        ctk.CTkLabel(self.frame_obs, text="OBS — Dofus Scene Guard").pack(anchor="w", padx=8, pady=(8, 2))
        self.var_obs_integration = ctk.BooleanVar(
            value=self.app.config.data.get("obs_integration_enabled", False)
        )
        self.sw_obs_integration = ctk.CTkSwitch(
            self.frame_obs, text=ui_text(self.app, "obs_connect", "Connecter OBS"), variable=self.var_obs_integration,
            command=self.save_obs_settings,
        )
        self.sw_obs_integration.pack(anchor="w", padx=8, pady=3)
        self.var_obs_auto_swap = ctk.BooleanVar(
            value=self.app.config.data.get("obs_auto_swap_enabled", False)
        )
        self.sw_obs_auto_swap = ctk.CTkSwitch(
            self.frame_obs, text=ui_text(self.app, "obs_auto_swap", "Auto-swap"), variable=self.var_obs_auto_swap,
            command=self.save_obs_settings,
        )
        self.sw_obs_auto_swap.pack(anchor="w", padx=8, pady=3)
        frame_obs_cam = ctk.CTkFrame(self.frame_obs, fg_color="transparent")
        frame_obs_cam.pack(fill="x", padx=8, pady=3)
        ctk.CTkLabel(frame_obs_cam, text=ui_text(self.app, "obs_error_scene", "Scène erreur :")).pack(side="left")
        self.entry_obs_full_cam = ctk.CTkEntry(frame_obs_cam, width=160)
        self.entry_obs_full_cam.insert(0, self.app.obs_bridge.profile.data["fallback_scene"])
        self.entry_obs_full_cam.pack(side="right")
        self.obs_profile_entries = {}
        for key, label in (
            ("stream_scene", "Scène stream :"),
            ("game_scene", "Scène Dofus :"),
            ("pause_scene", "Scène pause :"),
            ("microphone_source", "Source micro :"),
            ("camera_scene", "Scène caméra :"),
            ("camera_source", "Source caméra :"),
            ("capture_prefix", "Préfixe captures :"),
            ("max_captures", "Limite captures :"),
        ):
            row = ctk.CTkFrame(self.frame_obs, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(row, text=label).pack(side="left")
            entry = ctk.CTkEntry(row, width=180)
            entry.insert(0, str(self.app.obs_bridge.profile.data[key]))
            entry.pack(side="right")
            self.obs_profile_entries[key] = entry
        self.var_obs_dock = ctk.BooleanVar(value=self.app.obs_bridge.profile.data["dock_enabled"])
        ctk.CTkSwitch(self.frame_obs, text=ui_text(self.app, "obs_floating_dock", "Dock streaming flottant"), variable=self.var_obs_dock,
                      command=self.save_obs_profile).pack(anchor="w", padx=8, pady=3)
        self.btn_obs_profile = ctk.CTkButton(
            self.frame_obs, text=ui_text(self.app, "obs_save_profile", "Enregistrer le profil OBS"), command=self.save_obs_profile,
            fg_color=input_color, hover_color=input_hover,
        )
        self.btn_obs_profile.pack(fill="x", padx=8, pady=(3, 5))
        self.btn_obs_sync = ctk.CTkButton(
            self.frame_obs, text=ui_text(self.app, "obs_sync_team", "Synchroniser la team avec OBS"),
            command=self.sync_obs_team, fg_color=input_color, hover_color=input_hover,
        )
        self.btn_obs_sync.pack(fill="x", padx=8, pady=(3, 8))
        self.btn_obs_rebuild = ctk.CTkButton(
            self.frame_obs, text=ui_text(self.app, "obs_rebuild_sources", "Reconstruire les sources OBS"),
            command=self.rebuild_obs_team, fg_color="#9b3d1f", hover_color="#bd522a",
        )
        self.btn_obs_rebuild.pack(fill="x", padx=8, pady=(0, 5))
        self.lbl_obs_status = ctk.CTkLabel(
            self.frame_obs, text=self.app.obs_bridge.last_status,
            wraplength=390, justify="left", anchor="w",
        )
        self.lbl_obs_status.pack(fill="x", padx=8, pady=(0, 8))
        # OBS has its own complete panel; keep the general settings compact.
        self.frame_obs.pack_forget()
        try:
            obs_logo = Image.open(resource_path("resources", "skin", "obs", "obs-logo.png"))
            self.obs_logo_image = ctk.CTkImage(light_image=obs_logo, dark_image=obs_logo, size=(62, 34))
        except Exception:
            self.obs_logo_image = None
        self.btn_obs_window = ctk.CTkButton(
            self.scroll_container, text="", image=self.obs_logo_image, width=68, height=38,
            fg_color="transparent", hover_color=theme["panel_alt"], command=self.open_obs_settings,
        )

        self.obs_extension_row = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.obs_extension_row.pack(fill="x", padx=12, pady=(18, 2))
        ctk.CTkSwitch(
            self.obs_extension_row, text=ui_text(self.app, "obs_extension", "Extension OBS"), variable=self.var_obs_integration,
            command=self.toggle_obs_extension,
        ).pack(side="right")

        self.btn_close = ctk.CTkButton(self.scroll_container, text=self.app.i18n.t("settings_close", "Fermer"), fg_color="#7f8c8d", command=self.destroy)
        self.btn_close.pack(pady=(20, 10))
        if self.var_obs_integration.get():
            self.btn_obs_window.pack(anchor="e", padx=12, pady=(0, 8))
        close_after_pointer_leaves(self, delay_ms=10_000)

    def close_when_minimized(self, _event=None):
        if self.winfo_exists() and self.state() == "iconic":
            self.destroy()

    def _set_dofus_display_busy(self, busy):
        self._dofus_display_busy = busy
        state = "disabled" if busy else "normal"
        for button in self.dofus_display_buttons:
            try:
                button.configure(state=state)
            except tk.TclError:
                pass

    def _run_dofus_display_action(self, progress, action, success):
        if self._dofus_display_busy:
            return
        self._set_dofus_display_busy(True)
        self.lbl_dofus_display_status.configure(text=progress)

        def worker():
            self.app.dofus_settings._record(f"ACTION_START {action.__name__}")
            try:
                self._dofus_display_results.put((True, success(action())))
                self.app.dofus_settings._record("ACTION_OK")
            except DofusSettingsError as error:
                self.app.dofus_settings._record(f"ACTION_ERROR {error}")
                self._dofus_display_results.put((False, str(error)))
            except Exception as error:
                self.app.dofus_settings._record(f"ACTION_ERROR {type(error).__name__}: {error}")
                self._dofus_display_results.put(
                    (False, ui_text(
                        self.app, "dofus_display_unexpected_error",
                        "Erreur inattendue pendant l'opération : {error}", error=error,
                    ))
                )

        threading.Thread(target=worker, daemon=True).start()

    def _poll_dofus_display_results(self):
        try:
            while True:
                succeeded, message = self._dofus_display_results.get_nowait()
                self._set_dofus_display_busy(False)
                self.lbl_dofus_display_status.configure(text=message)
                if succeeded:
                    messagebox.showinfo(ui_text(self.app, "dofus_display_title", "Affichage Dofus"), message, parent=self)
                else:
                    messagebox.showerror(ui_text(self.app, "dofus_display_title", "Affichage Dofus"), message, parent=self)
        except queue.Empty:
            pass
        try:
            self.after(100, self._poll_dofus_display_results)
        except tk.TclError:
            pass

    def refresh_dofus_display_status(self):
        try:
            status = self.app.dofus_settings.status()
            if not status["available"]:
                text = ui_text(self.app, "dofus_display_unavailable", "Réglages Dofus RELEASE introuvables sur cet ordinateur.")
            else:
                profile = ui_text(self.app, "dofus_display_profile_ready", "profil prêt") if status["profile_exists"] else ui_text(self.app, "dofus_display_profile_missing", "profil à créer")
                process = ui_text(self.app, "dofus_display_game_open", "Dofus ouvert — opérations bloquées") if status["running"] else ui_text(self.app, "dofus_display_game_closed", "Dofus fermé — prêt")
                text = ui_text(
                    self.app, "dofus_display_status",
                    "RELEASE {version} · {accounts} compte(s) · {profile}\n{process} · Dernière sauvegarde : {backup}",
                    version=status["version"], accounts=status["accounts"], profile=profile,
                    process=process, backup=status["last_backup"],
                )
            self.lbl_dofus_display_status.configure(text=text)
        except Exception as error:
            self.lbl_dofus_display_status.configure(text=ui_text(
                self.app, "dofus_display_read_failed", "Lecture impossible : {error}", error=error,
            ))

    def capture_dofus_display_profile(self):
        self._run_dofus_display_action(
            ui_text(self.app, "dofus_display_capture_progress", "Enregistrement du profil maître JEU CLASSIQUE…"),
            self.app.dofus_settings.capture_master_profile,
            lambda result: (
                ui_text(
                    self.app, "dofus_display_capture_success",
                    "Profil JEU CLASSIQUE enregistré. Interface normale : {normal} · Combat : {fight} · {shared} réglage(s) global(aux) et {account} réglage(s) de compte.",
                    normal=result["normal"], fight=result["fight"], shared=result["shared"], account=result["account"],
                )
                + ("\n\n" + "\n".join(result.get("warnings", [])) if result.get("warnings") else "")
            ),
        )

    def apply_dofus_display_profile(self):
        if not messagebox.askyesno(
            ui_text(self.app, "dofus_display_apply_title", "Appliquer JEU CLASSIQUE"),
            ui_text(self.app, "dofus_display_apply_confirm", "Tous les clients Dofus doivent être fermés. DOSOFT créera automatiquement un point de retour, puis appliquera le profil aux réglages d'interface de tous les comptes. Continuer ?"),
            parent=self,
        ):
            return
        self._run_dofus_display_action(
            ui_text(self.app, "dofus_display_apply_progress", "Sauvegarde de sécurité puis application à tous les comptes…"),
            self.app.dofus_settings.apply_master_profile,
            lambda result: (
                ui_text(
                    self.app, "dofus_display_apply_success",
                    "JEU CLASSIQUE appliqué à {accounts} compte(s). Point de retour créé : {rollback}",
                    accounts=result["accounts"], rollback=result["rollback"].name,
                )
            ),
        )

    def backup_dofus_display(self):
        self._run_dofus_display_action(
            ui_text(self.app, "dofus_display_backup_progress", "Création d'une sauvegarde locale vérifiée…"),
            lambda: self.app.dofus_settings.create_backup("manuel"),
            lambda path: ui_text(self.app, "dofus_display_backup_success", "Sauvegarde créée et vérifiée : {name}", name=path.name)
            + ("\n\n" + self.app.dofus_settings.backup_warning(path) if self.app.dofus_settings.backup_warning(path) else ""),
        )

    def restore_dofus_display(self):
        latest = self.app.dofus_settings.latest_backup()
        if latest is None:
            messagebox.showerror(
                ui_text(self.app, "dofus_display_title", "Affichage Dofus"),
                ui_text(self.app, "dofus_display_no_backup", "Aucune sauvegarde DOSOFT n'est disponible."), parent=self,
            )
            return
        if not messagebox.askyesno(
            ui_text(self.app, "dofus_display_restore_title", "Restaurer les réglages Dofus"),
            ui_text(
                self.app, "dofus_display_restore_confirm",
                "Restaurer la dernière sauvegarde ?\n\n{name}\n\nUn nouveau point de retour sera créé avant la restauration.", name=latest.name,
            ),
            parent=self,
        ):
            return
        self._run_dofus_display_action(
            ui_text(self.app, "dofus_display_restore_progress", "Création du point de retour puis restauration…"),
            self.app.dofus_settings.restore_latest_backup,
            lambda result: (
                ui_text(
                    self.app, "dofus_display_restore_success",
                    "Réglages restaurés depuis {archive} ({files} fichier(s)). Point de retour : {rollback}",
                    archive=result["archive"].name, files=result["files"], rollback=result["rollback"].name,
                )
            ),
        )

    def create_theme_selector(self, name, variable, available_themes, on_change):
        """Three numbered theme slots; future slots remain visibly unavailable."""
        frame = ctk.CTkFrame(self.scroll_container)
        frame.pack(fill="x", padx=10, pady=5)
        label = ctk.CTkLabel(frame, text=ui_text(self.app, "settings_theme", "Thème {name}", name=name))
        label.pack(side="left", padx=8, pady=8)
        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(side="right", padx=8, pady=6)
        buttons = {}
        for slot in ("1", "2", "3"):
            is_available = slot in available_themes
            button = ctk.CTkButton(
                button_frame, text=slot, width=34, height=28, corner_radius=7,
                command=lambda selected=slot: self.select_theme_slot(variable, selected, on_change),
            )
            if not is_available:
                button.configure(
                    state="disabled", fg_color="#0b0b0b", hover_color="#0b0b0b",
                    text_color="#f4f4f4", text_color_disabled="#f4f4f4",
                    border_width=1, border_color="#f4f4f4",
                )
            button.pack(side="left", padx=3)
            buttons[slot] = (button, is_available, variable)
        self.theme_selector_buttons[name] = buttons
        self.refresh_theme_selector_states()
        return frame, label

    def select_theme_slot(self, variable, choice, on_change):
        variable.set(choice)
        on_change(choice)

    def refresh_theme_selector_states(self):
        theme = self.parent.game_theme
        for buttons in self.theme_selector_buttons.values():
            for slot, (button, is_available, variable) in buttons.items():
                if not is_available:
                    continue
                is_selected = variable.get() == slot
                button.configure(
                    fg_color=theme["accent"] if is_selected else theme["panel_alt"],
                    hover_color=theme["accent_hover"] if is_selected else theme["panel"],
                    text_color="#101010" if is_selected else theme["title"],
                    border_width=2 if is_selected else 0,
                    border_color=theme["border"] if is_selected else theme["panel_alt"],
                )

    def save_settings(self):
        previous_language = self.app.config.data.get("language", "fr")
        selected_language = next(
            (code for code, name in LANGUAGE_NAMES.items() if name == self.var_language.get()),
            "fr",
        )
        self.app.config.data["radial_menu_active"] = self.var_radial.get()
        self.app.config.data["language"] = selected_language
        self.app.config.data["keyboard_layout"] = self.var_keyboard_layout.get()
        self.app.config.data["wakfu_theme"] = self.var_wakfu_theme.get()
        self.app.config.data["unity_theme"] = self.var_unity_theme.get()
        self.app.config.data["retro_theme"] = self.var_retro_theme.get()
        self.app.config.data["fast_switch_team_disabled"] = self.var_fast_switch_team_disabled.get()
        self.app.config.data["hotkey_chord_overlap_enabled"] = self.var_hotkey_overlap.get()
        self.app.config.data["character_bar_compact"] = self.var_character_bar_compact.get()
        self.app.config.data["obs_integration_enabled"] = self.var_obs_integration.get()
        self.app.config.data["obs_full_cam_scene"] = self.entry_obs_full_cam.get().strip() or "FULL_CAM"
        self.app.config.data["notif_api_mode"] = self.notification_mode_labels.get(self.var_notif_api.get(), "Automatique")
        self.app.i18n.set_locale(selected_language)
        self.app.keymaps.set_layout(self.var_keyboard_layout.get())
        self.app.setup_hotkeys()
        if not self.app.config.save():
            return False
        self.app.obs_bridge.set_auto_swap(self.var_obs_auto_swap.get())
        bar = getattr(self.app, "character_bar", None)
        if bar:
            bar.update_accounts(
                self.app.logic.all_accounts,
                self.app.config.data.get("game_version", "Unity"),
                immediate=True,
            )
        self.parent.apply_game_theme()
        self.refresh_theme_selector_states()
        self.parent.apply_translations()
        self.apply_translations()

        if previous_language != selected_language:
            self.title(self.app.i18n.t("settings_title", "⚙️ Paramètres"))
        return True

    def refresh_character_bar_option(self, key, value, refresh_hotkeys=False):
        """Apply one quick-bar option without rebuilding every settings module."""
        self.app.config.data[key] = bool(value)
        if not self.app.config.save():
            return
        if refresh_hotkeys:
            self.app.setup_hotkeys()
        bar = getattr(self.app, "character_bar", None)
        if bar:
            bar.update_accounts(
                self.app.logic.all_accounts,
                self.app.config.data.get("game_version", "Unity"),
                immediate=True,
            )
            if key == "character_bar_compact":
                bar.restore_after_presentation_change()
        # One real scan picks up pages launched while the settings were open.
        self.after_idle(self.app.refresh)

    def on_character_bar_compact_change(self):
        self.refresh_character_bar_option(
            "character_bar_compact", self.var_character_bar_compact.get()
        )

    def on_fast_switch_team_change(self):
        self.refresh_character_bar_option(
            "fast_switch_team_disabled",
            self.var_fast_switch_team_disabled.get(),
            refresh_hotkeys=True,
        )

    def on_hotkey_overlap_change(self):
        enabled = bool(self.var_hotkey_overlap.get())
        if enabled:
            accepted = messagebox.askyesno(
                ui_text(self.app, "hotkey_overlap_warning_title", "Option expérimentale"),
                ui_text(
                    self.app,
                    "hotkey_overlap_warning_message",
                    "Ce mode permet de maintenir Alt, Ctrl ou Maj et d’enchaîner la touche principale du raccourci.\n\nIl peut provoquer des répétitions ou des saisies inattendues après un changement de fenêtre. Son utilisation n’est pas recommandée et les incidents causés par cette option ne sont pas pris en charge.\n\nActiver quand même ?",
                ),
                parent=self,
            )
            if not accepted:
                self.var_hotkey_overlap.set(False)
                return
        self.app.config.data["hotkey_chord_overlap_enabled"] = enabled
        self.app._pressed_hotkey_scans.clear()
        self.app.config.save()

    def save_obs_settings(self):
        """Persist OBS controls without rebuilding the settings UI."""
        self.app.config.data["obs_integration_enabled"] = self.var_obs_integration.get()
        if self.var_obs_integration.get() and not self.app.obs_bridge.profile.exists:
            if messagebox.askyesno(
                ui_text(self.app, "obs_configure_title", "Configurer OBS"),
                ui_text(self.app, "obs_profile_create_confirm", "Aucun profil OBS n'existe. Créer le profil avec les valeurs affichées ?"),
                parent=self,
            ):
                self.save_obs_profile()
            else:
                self.var_obs_integration.set(False)
                self.app.config.data["obs_integration_enabled"] = False
        if not self.app.config.save():
            return False
        self.app.obs_bridge.set_auto_swap(self.var_obs_auto_swap.get())
        return True

    def save_obs_profile(self):
        """Write the user-editable OBS profile beside DOSOFT."""
        profile = self.app.obs_bridge.profile.data
        profile["fallback_scene"] = self.entry_obs_full_cam.get().strip() or "FULL_CAM"
        for key, entry in self.obs_profile_entries.items():
            profile[key] = entry.get().strip() or profile[key]
        try:
            profile["max_captures"] = max(1, int(profile["max_captures"]))
        except ValueError:
            profile["max_captures"] = 12
        profile["dock_enabled"] = self.var_obs_dock.get()
        if not self.app.obs_bridge.profile.save():
            messagebox.showerror(
                ui_text(self.app, "obs_profile_title", "Profil OBS"),
                self.app.obs_bridge.profile.last_error,
                parent=self,
            )
            return False
        self.app.obs_bridge._record("OBS : profil enregistré : " + str(self.app.obs_bridge.profile.path))
        self.app.refresh_obs_stream_dock()
        self.refresh_obs_status()
        return True

    def open_obs_settings(self):
        if not self.app.obs_bridge.enabled:
            return
        self.parent.open_obs_extension()

    def toggle_obs_extension(self):
        if self.var_obs_integration.get():
            self.app.obs_bridge.activate()
            self.parent.update_obs_quick_controls()
            if not self.btn_obs_window.winfo_manager():
                self.btn_obs_window.pack(anchor="e", padx=12, pady=(0, 8))
            self.open_obs_settings()
        else:
            self.app.obs_bridge.deactivate()
            self.parent.update_obs_quick_controls()
            self.var_obs_auto_swap.set(False)
            self.btn_obs_window.pack_forget()
            window = getattr(self.parent, "obs_settings_window", None)
            if window is not None and window.winfo_exists():
                window.destroy()
            self.app.refresh_obs_stream_dock()

    def sync_obs_team(self):
        self.save_obs_settings()
        self.app.sync_obs_team()
        self.after(500, self.refresh_obs_status)

    def rebuild_obs_team(self):
        self.save_obs_settings()
        self.app.rebuild_obs_team()
        self.after(500, self.refresh_obs_status)

    def refresh_obs_status(self):
        if hasattr(self, "lbl_obs_status"):
            self.lbl_obs_status.configure(text=self.app.obs_bridge.last_status)

    def on_wakfu_theme_change(self, _choice):
        self.save_settings()

    def on_unity_theme_change(self, _choice):
        self.save_settings()

    def on_retro_theme_change(self, _choice):
        self.save_settings()
            
    def on_notif_api_change(self, choice):
        self.app.config.data["notif_api_mode"] = self.notification_mode_labels.get(choice, "Automatique")
        self.app.config.save()
        
        rep = messagebox.askyesno(
            ui_text(self.app, "restart_required_title", "Redémarrage requis"),
            ui_text(self.app, "restart_autofocus_message", "Pour appliquer le changement de moteur d'Autofocus, DOSOFT doit être redémarré"),
            parent=self
        )
        if rep:
            # On utilise ta fonction de fermeture native qui nettoie tout correctement
            self.app.quit_app()

    def open_retro_autofocus_log(self):
        """Create and open the compact diagnostic trace for support reports."""
        write_retro_debug("LOG_OPENED_FROM_SETTINGS")
        log_path = get_retro_debug_log_path()
        try:
            os.startfile(str(log_path))
        except OSError as exc:
            messagebox.showerror(
                ui_text(self.app, "retro_log_title", "Journal Auto-Focus Rétro"),
                ui_text(self.app, "retro_log_open_failed", "Impossible d'ouvrir :\n{path}\n\n{error}", path=log_path, error=exc),
                parent=self,
            )

    def destroy(self):
        """Detach settings-only buttons before Tk destroys their window."""
        if hasattr(self, "obs_settings_window") and self.obs_settings_window.winfo_exists():
            self.obs_settings_window.destroy()
        for key, button in (
            ("radial_menu_hotkey", getattr(self, "btn_radial_hotkey", None)),
            ("team_switch_key", getattr(self, "btn_team_switch_hotkey", None)),
        ):
            if self.parent.hotkey_btns.get(key) is button:
                self.parent.hotkey_btns.pop(key, None)
        super().destroy()
            


    def apply_translations(self):
        self.title(self.app.i18n.t("settings_title", "⚙️ Paramètres"))
        self.lbl_settings_radial.configure(text=self.app.i18n.t("settings_radial", "Roue de Focus (Radiale)"))
        self.sw_radial.configure(text=self.app.i18n.t("settings_radial_enable", "Activer la roue"))
        self.lbl_hk.configure(text=self.app.i18n.t("settings_hotkey", "Raccourci :"))
        self.lbl_dofus_display_title.configure(text=ui_text(self.app, "dofus_display_title", "Affichage Dofus"))
        self.lbl_dofus_display_help.configure(text=ui_text(
            self.app, "dofus_display_help",
            "Préparez votre interface parfaite dans Dofus, fermez ce compte en dernier, puis enregistrez JEU CLASSIQUE. Fermez tous les clients avant chaque opération.",
        ))
        for button, key, default in self.dofus_display_button_keys:
            button.configure(text=ui_text(self.app, key, default))
        self.lbl_fast_switch_team.configure(text=ui_text(self.app, "settings_fast_switch", "Fast Switch TEAM"))
        self.sw_fast_switch_team_disabled.configure(text=ui_text(self.app, "disable", "Désactiver"))
        self.lbl_hotkey_overlap.configure(text=ui_text(self.app, "settings_hotkey_overlap", "Superposer les raccourcis"))
        self.sw_hotkey_overlap.configure(text=ui_text(self.app, "enable", "Activer"))
        self.lbl_team_switch_hotkey.configure(text=ui_text(self.app, "settings_team_switch_hotkey", "Raccourci switch de mode TEAM"))
        self.lbl_character_bar_format.configure(text=ui_text(self.app, "settings_compact_character_bar", "Barre perso minimale"))
        self.sw_character_bar_compact.configure(text=ui_text(self.app, "enable", "Activer"))
        self.lbl_wakfu_theme.configure(text=ui_text(self.app, "settings_theme", "Thème {name}", name="WAKFU"))
        self.lbl_unity_theme.configure(text=ui_text(self.app, "settings_theme", "Thème {name}", name="UNITY"))
        self.lbl_retro_theme.configure(text=ui_text(self.app, "settings_theme", "Thème {name}", name="Rétro"))
        self.lbl_debug.configure(text=ui_text(self.app, "settings_autofocus_engine", "Moteur Auto-Focus (dépannage)"))
        self.lbl_retro_log.configure(text=ui_text(self.app, "settings_retro_diagnostic", "Diagnostic Auto-Focus Rétro"))
        self.btn_retro_log.configure(text=ui_text(self.app, "settings_open_log", "Ouvrir le journal"))
        current_mode = self.notification_mode_labels.get(self.var_notif_api.get(), "Automatique")
        self.notification_mode_labels = {
            ui_text(self.app, "notification_mode_automatic", "Automatique"): "Automatique",
            ui_text(self.app, "notification_mode_polling", "Polling"): "Polling",
        }
        self.combo_debug.configure(values=list(self.notification_mode_labels))
        self.var_notif_api.set(next(
            (label for label, value in self.notification_mode_labels.items() if value == current_mode),
            next(iter(self.notification_mode_labels)),
        ))
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
        # Taille validée pour la bêta : 700x880 à l'écran, barre de titre Windows
        # comprise (Tk reçoit ici les 700x850 de la zone cliente).
        win_w = 700
        win_h = 850
        x_pos = int((screen_w / 2) - (win_w / 2))
        y_pos = int((screen_h / 2) - (win_h / 2))
        self.root.geometry(f"{win_w}x{win_h}+{x_pos}+{y_pos}") 
        self.root.minsize(win_w, win_h)
        self.root.maxsize(win_w, win_h)
        self.root.resizable(False, False)
        
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.original_app_refresh = self.app.refresh

        

        if os.path.exists("logo.ico"):
            try: self.root.iconbitmap("logo.ico")
            except: pass
                
        self.is_listening = False
        self.is_visible = True 
        cfg = self.app.config.data 
        self.game_theme = selected_game_theme(cfg)
        
        self.var_tooltips = ctk.BooleanVar(value=cfg.get("show_tooltips", True))
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.overrideredirect(True)
        self.tooltip.attributes("-topmost", True)
        self.tooltip_lbl = tk.Label(self.tooltip, text="", fg="#ecf0f1", bg="#2c3e50", font=("Segoe UI", 9), padx=6, pady=3, relief="solid", borderwidth=1)
        self.tooltip_lbl.pack()
        self.tooltip.withdraw() 
        
        self.hotkey_btns = {}
        self.hotkey_clear_buttons = []
        self.hotkey_labels = {}
        self.tooltip_i18n_map = {}

        # Fond texturé, réservé aux trois moteurs pour donner de la profondeur
        # aux respirations entre les cartes.
        self.wakfu_background_texture = None
        texture_name = self.game_theme.get("background_image")
        texture_path = resource_path("resources", "skin", texture_name) if texture_name else ""
        if texture_path and os.path.exists(texture_path):
            self.wakfu_background_texture = self.create_rounded_theme_image(texture_path, (670, 850), 18)
        self.lbl_wakfu_background = ctk.CTkLabel(
            self.root, text="", image=self.wakfu_background_texture, fg_color="transparent",
            width=670, height=850,
        )
        self.lbl_wakfu_background.place(x=15, y=0)
        self.lbl_wakfu_background.lower()

        self.header_f = ctk.CTkFrame(self.root, fg_color="transparent")
        self.header_f.pack(fill="x", padx=15, pady=(15, 5))
        
        self.lbl_app_title = ctk.CTkLabel(self.header_f, text=APP_TITLE, font=ctk.CTkFont(size=20, weight="bold"))

        self.lbl_app_title.pack(side="left")
        
        self.btn_settings = ctk.CTkButton(self.header_f, text=self.app.i18n.t("header_settings", "⚙️ Paramètres"), fg_color="#34495e", hover_color="#2c3e50", width=120, command=self.open_settings)
        self.btn_settings.pack(side="right")
        self.bind_i18n_tooltip(self.btn_settings, "tooltip_settings", "Paramétrer la roue radiale")

        self.btn_off = ctk.CTkButton(self.header_f, text=self.app.i18n.t("header_off", "🔴 OFF"), fg_color="#c0392b", hover_color="#e74c3c", width=60, command=self.app.quit_app)
        self.btn_off.pack(side="right", padx=(0, 10))
        self.bind_i18n_tooltip(self.btn_off, "tooltip_off", "Fermer complètement DOSOFT")

        # Bandeau partagé des trois moteurs, avec une direction artistique propre
        # à chaque thème.
        self.frame_module_banner = ctk.CTkFrame(
            self.root, height=58, corner_radius=9, fg_color="#172126",
        )
        self.frame_module_banner.pack_propagate(False)
        texture_name = self.game_theme.get("background_image")
        texture_path = resource_path("resources", "skin", texture_name) if texture_name else ""
        self.wakfu_banner_texture = None
        if texture_path and os.path.exists(texture_path):
            self.wakfu_banner_texture = self.create_rounded_theme_image(texture_path, (670, 58), 13)
        self.lbl_module_texture = ctk.CTkLabel(
            self.frame_module_banner, text="", image=self.wakfu_banner_texture,
            fg_color="transparent",
        )
        self.lbl_module_texture.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.frame_module_banner_content = ctk.CTkFrame(
            self.frame_module_banner, fg_color="transparent"
        )
        self.frame_module_banner_content.pack(fill="both", expand=True)
        self.lbl_module_title = ctk.CTkLabel(
            self.frame_module_banner_content, text="WAKFU", font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_module_title.place(relx=0.5, rely=0.34, anchor="center")
        self.lbl_module_subtitle = ctk.CTkLabel(
            self.frame_module_banner_content, text=ui_text(self.app, "group_management", "GESTION DE GROUPE"), font=ctk.CTkFont(size=11, weight="bold")
        )
        self.lbl_module_subtitle.place(relx=0.5, rely=0.72, anchor="center")

        self.frame_mode = ctk.CTkFrame(self.root)
        self.frame_mode.pack(fill="x", padx=15, pady=5)
        
        self.lbl_controls = ctk.CTkLabel(self.frame_mode, text=self.app.i18n.t("label_controls", "Contrôler :"))
        self.lbl_controls.pack(side="left", padx=10, pady=5)
        
        self.combo_mode = ctk.CTkOptionMenu(self.frame_mode, values=["ALL", "Team 1", "Team 2"], command=self.on_mode_change)
        self.combo_mode.set(cfg.get("current_mode", "ALL"))
        self.combo_mode.pack(side="left", padx=5, pady=5)

        self.lbl_versions = ctk.CTkLabel(self.frame_mode, text=self.app.i18n.t("label_versions", "Versions :"))
        self.lbl_versions.pack(side="left", padx=(20, 5), pady=5)
        
        self.version_selector = ctk.CTkFrame(self.frame_mode, fg_color="transparent")
        self.version_selector.pack(side="left", padx=5, pady=3)
        self.version_buttons = {}
        self.version_images = {}
        for version, icon_name in (("Unity", "unity"), ("Rétro", "retro"), ("Wakfu", "wakfu")):
            # Le médaillon Rétro est plus rond : une largeur légèrement réduite
            # préserve sa silhouette au lieu de l'écraser dans le carré commun.
            icon_size = (24, 28) if version == "Rétro" else (28, 28)
            self.version_images[version] = self.load_selector_image(icon_name, size=icon_size)
            button = ctk.CTkButton(
                self.version_selector,
                text="",
                image=self.version_images[version],
                width=36,
                height=34,
                corner_radius=7,
                command=lambda selected=version: self.on_version_change(selected),
            )
            button.pack(side="left", padx=2)
            self.version_buttons[version] = button
        self.update_version_selector(cfg.get("game_version", "Unity"))

        self.obs_quick_frame = ctk.CTkFrame(self.frame_mode, fg_color="transparent")
        try:
            obs_quick_logo = Image.open(resource_path("resources", "skin", "obs", "obs-logo.png"))
            self.obs_quick_image = ctk.CTkImage(
                light_image=obs_quick_logo, dark_image=obs_quick_logo, size=(50, 34)
            )
        except Exception:
            self.obs_quick_image = None
        self.btn_obs_quick = ctk.CTkButton(
            self.obs_quick_frame, text="", image=self.obs_quick_image, width=60, height=42,
            fg_color="#35375c", hover_color="#9ebd05", command=self.open_obs_extension,
        )
        self.btn_obs_quick.pack(side="left", padx=2)
        self.btn_obs_emergency = ctk.CTkButton(
            self.obs_quick_frame, text="↻", width=40, height=42,
            font=ctk.CTkFont(size=22, weight="bold"), fg_color="#a62020", hover_color="#d43a3a",
            command=self.emergency_restart_obs,
        )
        self.btn_obs_emergency.pack(side="left", padx=2)
        self.bind_i18n_tooltip(self.btn_obs_quick, "tooltip_obs_open", "Ouvrir l'assistant OBS")
        self.bind_i18n_tooltip(
            self.btn_obs_emergency, "tooltip_obs_emergency",
            "Redémarrage d'urgence : supprimer puis recréer les captures DOSOFT",
        )
        self.update_obs_quick_controls()

        self.var_autofocus = ctk.BooleanVar(value=cfg.get(self._autofocus_config_key(), False))
        self.autofocus_image = self.load_selector_image(self.game_theme.get("focus_icon", "focus"))
        self.chk_autofocus = ctk.CTkButton(
            self.frame_mode, text="", image=self.autofocus_image,
            width=36, height=34, corner_radius=7, command=self.toggle_autofocus,
        )
        self.btn_retro_autofocus_settings = ctk.CTkButton(
            self.frame_mode, text="⚙", width=46, height=34, corner_radius=7,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=self.game_theme["panel_alt"],
            hover_color=self.game_theme["accent_hover"],
            command=self.open_retro_autofocus_settings,
        )
        self.retro_autofocus_settings_window = None
        
        if cfg.get("game_version", "Unity") == "Rétro":
            self.chk_autofocus.pack(side="left", padx=(15, 5))
        if cfg.get("game_version", "Unity") == "Rétro":
            self.btn_retro_autofocus_settings.pack(side="left", padx=(0, 5))
            
        self.bind_i18n_tooltip(self.chk_autofocus, "tooltip_auto_focus", "Focus automatiquement la page Rétro lors d'une notification")
        self.bind_i18n_tooltip(
            self.btn_retro_autofocus_settings,
            "tooltip_retro_autofocus_settings",
            "Choisir les notifications qui déclenchent l’Auto-Focus Rétro",
        )

        self.frame_retro_layout = ctk.CTkFrame(self.root, corner_radius=10)
        self.lbl_retro_layout = ctk.CTkLabel(
            self.frame_retro_layout,
            text=ui_text(self.app, "retro_windows_title", "Fenêtres Dofus Rétro"),
            font=ctk.CTkFont(weight="bold"),
        )
        self.lbl_retro_layout.pack(side="left", padx=(10, 8), pady=7)
        self.btn_retro_maximize = ctk.CTkButton(
            self.frame_retro_layout, text=ui_text(self.app, "retro_windows_maximize", "▣ Agrandir tout"), width=128, height=30,
            command=self.maximize_retro_windows,
        )
        self.btn_retro_maximize.pack(side="right", padx=(4, 8), pady=6)
        self.btn_retro_tile = ctk.CTkButton(
            self.frame_retro_layout, text=ui_text(self.app, "retro_windows_tile", "▦ Ranger les fenêtres"), width=158, height=30,
            command=self.tile_retro_windows,
        )
        self.btn_retro_tile.pack(side="right", padx=4, pady=6)
        self.bind_i18n_tooltip(
            self.btn_retro_maximize, "tooltip_retro_maximize",
            "Maximiser toutes les fenêtres Dofus Rétro détectées",
        )
        self.bind_i18n_tooltip(
            self.btn_retro_tile, "tooltip_retro_tile",
            "Remplir un écran avec les fenêtres Rétro, en grille 4 × 2 pour huit comptes",
        )
        if cfg.get("game_version", "Unity") == "Rétro":
            self.frame_retro_layout.pack(fill="x", padx=15, pady=(0, 5))

        self.frame_keys = ctk.CTkFrame(self.root)
        self.frame_keys.pack(fill="x", padx=15, pady=10)
        self.lbl_keyboard_shortcuts = ctk.CTkLabel(self.frame_keys, text=self.app.i18n.t("label_keyboard_shortcuts", "Raccourcis Clavier"), font=ctk.CTkFont(weight="bold"))
        self.lbl_keyboard_shortcuts.pack(pady=(5, 3))
        self.frame_hotkey_grid = ctk.CTkFrame(self.frame_keys, fg_color="transparent")
        self.frame_hotkey_grid.pack(anchor="center", pady=(0, 5))

        self.create_hotkey_row(self.frame_hotkey_grid, "hotkey_prev", "prev_key", 1, 0, "tooltip_prev")
        self.create_hotkey_row(self.frame_hotkey_grid, "hotkey_next", "next_key", 1, 3, "tooltip_next")
        self.create_hotkey_row(self.frame_hotkey_grid, "hotkey_leader", "leader_key", 2, 0, "tooltip_leader")
        self.create_hotkey_row(self.frame_hotkey_grid, "hotkey_toggle_ui", "toggle_app_key", 2, 3, "tooltip_toggle_ui")
        self.create_hotkey_row(self.frame_hotkey_grid, "hotkey_refresh", "refresh_key", 1, 6, "tooltip_refresh")
        self.create_hotkey_row(self.frame_hotkey_grid, "hotkey_quit", "quit_key", 2, 6, "tooltip_quit")

        self.frame_actions = ctk.CTkFrame(self.root)
        self.frame_actions.pack(fill="x", padx=15, pady=5)

        self.volume_image = self.load_selector_image(self.game_theme.get("volume_icon", "volume"), size=(28, 28))
        self.lbl_volume = ctk.CTkLabel(self.frame_actions, text="", image=self.volume_image, width=32)
        self.lbl_volume.pack(side="left", padx=10)
        self.slider_volume = ctk.CTkSlider(self.frame_actions, from_=0, to=100, command=self.on_volume_change, width=150)
        self.slider_volume.set(cfg.get("volume_level", 50))
        self.slider_volume.pack(side="left", padx=10, pady=10)

        self.var_character_bar = ctk.BooleanVar(value=cfg.get("character_bar_visible", False))
        self.sw_character_bar = ctk.CTkSwitch(
            self.frame_actions, text=ui_text(self.app, "character_bar", "Barre persos"), variable=self.var_character_bar,
            command=self.toggle_character_bar, width=112,
        )
        self.sw_character_bar.pack(side="left", padx=(8, 4))
        
        self.btn_close_all = ctk.CTkButton(self.frame_actions, text=self.app.i18n.t("btn_close_team", "Fermer Team"), fg_color="#c0392b", hover_color="#e74c3c", command=self.close_all_and_refresh, width=120)
        self.btn_close_all.pack(side="right", padx=10)
        
        self.btn_reset = ctk.CTkButton(self.frame_actions, text=self.app.i18n.t("btn_reset_settings", "Reset Settings"), fg_color="#7f8c8d", hover_color="#95a5a6", command=self.reset_all, width=120)
        self.btn_reset.pack(side="right", padx=10)

        # --- NOUVEAU DESIGN : Barre Comptes Actifs avec Binds Avancés ---
        self.pill_frame = ctk.CTkFrame(self.root, fg_color="#3b4252", corner_radius=8)
        self.pill_frame.pack(fill="x", padx=15, pady=(10, 0), ipadx=5, ipady=2)

        self.lbl_accounts = ctk.CTkLabel(self.pill_frame, text=self.app.i18n.t("label_active_accounts", "Comptes actifs"), font=ctk.CTkFont(size=13, weight="normal"), text_color="#ecf0f1")
        self.lbl_accounts.place(relx=0.5, rely=0.5, anchor="center")

        self.btn_manage_binds = ctk.CTkButton(self.pill_frame, text="⚙️", width=28, height=28,
                                        fg_color="#2c3e50", hover_color="#1a252f", corner_radius=6,
                                        command=self.open_bind_manager)
        self.btn_manage_binds.pack(side="right", padx=5, pady=4)
        self.bind_i18n_tooltip(self.btn_manage_binds, "tooltip_manage_binds", "Gérer les raccourcis avancés par personnage")

        self.scroll_frame = ctk.CTkScrollableFrame(self.root)
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=(5, 10))

        self.frame_fast_command = ctk.CTkFrame(self.root, fg_color="#263641", corner_radius=8, height=122)
        self.frame_fast_command.pack_propagate(False)
        self.frame_fast_command_row = ctk.CTkFrame(self.frame_fast_command, fg_color="transparent")
        self.frame_fast_command_row.pack(fill="x", padx=2, pady=(2, 0))
        self.follow_image = self.load_selector_image(self.game_theme.get("follow_icon", "follow"), size=(39, 39))
        self.lbl_fast_follow_icon = ctk.CTkLabel(self.frame_fast_command_row, text="", image=self.follow_image, width=42)
        self.lbl_fast_follow_icon.pack(side="left", padx=(10, 2), pady=7)
        self.lbl_fast_command = ctk.CTkLabel(self.frame_fast_command_row, text=ui_text(self.app, "wakfu_follow_title", "Commande rapide"), font=ctk.CTkFont(weight="bold"))
        self.lbl_fast_command.pack(side="left", padx=(2, 6), pady=7)
        self.lbl_fast_command_value = ctk.CTkLabel(
            self.frame_fast_command_row, text=ui_text(self.app, "wakfu_follow_no_leader", "Définis un meneur pour générer la commande."),
            text_color="#d8e2e8"
        )
        self.lbl_fast_command_value.pack(side="left", padx=4, pady=7)
        self.btn_copy_fast_command = ctk.CTkButton(
            self.frame_fast_command_row, text=ui_text(self.app, "copy", "Copier"), width=65, height=26,
            fg_color="#2f6b57", hover_color="#3c8069", state="disabled",
            command=self.copy_fast_command,
        )
        self.btn_copy_fast_command.pack(side="right", padx=8, pady=7)
        self.fast_invite_separator = ctk.CTkFrame(self.frame_fast_command, height=1, fg_color="#47606f")
        self.fast_invite_separator.pack(fill="x", padx=10, pady=(2, 2))
        self.frame_fast_invite_row = ctk.CTkFrame(self.frame_fast_command, fg_color="transparent")
        self.frame_fast_invite_row.pack(fill="x", padx=2, pady=(0, 0))
        self.group_image = self.load_selector_image(self.game_theme.get("group_icon", "groupe"), size=(39, 39))
        self.lbl_fast_group_icon = ctk.CTkLabel(self.frame_fast_invite_row, text="", image=self.group_image, width=42)
        self.lbl_fast_group_icon.pack(side="left", padx=(10, 2), pady=7)
        self.lbl_fast_invite = ctk.CTkLabel(self.frame_fast_invite_row, text=ui_text(self.app, "wakfu_invite_title", "Invitation de groupe"), font=ctk.CTkFont(weight="bold"))
        self.lbl_fast_invite.pack(side="left", padx=(2, 6), pady=7)
        self.lbl_fast_invite_value = ctk.CTkLabel(
            self.frame_fast_invite_row, text=ui_text(self.app, "wakfu_invite_no_leader", "Définis un meneur pour générer les invitations."),
            text_color="#d8e2e8", justify="left", anchor="w", wraplength=350,
        )
        self.lbl_fast_invite_value.pack(side="left", padx=4, pady=7, fill="x", expand=True)
        self.btn_copy_fast_invites = ctk.CTkButton(
            self.frame_fast_invite_row, text=ui_text(self.app, "copy", "Copier"), width=65, height=26,
            fg_color="#2f6b57", hover_color="#3c8069", state="disabled",
            command=self.copy_fast_invites,
        )
        self.btn_copy_fast_invites.pack(side="right", padx=8, pady=7)
        
        # --- CORRECTION PIED DE PAGE ---
        self.frame_footer = ctk.CTkFrame(self.root, fg_color="transparent")
        self.frame_footer.pack(side="bottom", fill="x", padx=15, pady=(0, 8))
        
        self.btn_refresh = ctk.CTkButton(self.frame_footer, text=self.app.i18n.t("btn_refresh", "Rafraîchir"), command=self.original_app_refresh, width=80)
        self.btn_refresh.pack(side="left")

        self.btn_sort_win = ctk.CTkButton(self.frame_footer, text=self.app.i18n.t("btn_sort_taskbar", "Trier Barre Windows"), fg_color="#8e44ad", hover_color="#9b59b6", command=self.trigger_sort_taskbar, width=120)
        self.btn_sort_win.pack(side="left", padx=5)
        
        self.chk_tooltips = ctk.CTkCheckBox(self.frame_footer, text=self.app.i18n.t("label_tooltips", "Bulles"), variable=self.var_tooltips, command=self.toggle_tooltips_setting, width=60)
        self.chk_tooltips.pack(side="left", padx=15)

        self.lbl_obs_connection = ctk.CTkLabel(
            self.frame_footer, text="", width=118, height=26, corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        
        self.btn_hide = ctk.CTkButton(self.frame_footer, text=self.app.i18n.t("btn_hide_ui", "Cacher l'UI"), command=self.toggle_visibility, fg_color="transparent", border_width=1, width=70)
        self.btn_hide.pack(side="right")
        if self.app.obs_bridge.enabled:
            self.lbl_obs_connection.pack(side="right", padx=(0, 6))
        self.root.after(250, self.poll_obs_connection_badge)

        # Les retours sont des toasts temporaires : aucun conteneur permanent ne
        # vient donc casser la finition entre Fast Commande et le pied de page.
        self.lbl_feedback = ctk.CTkLabel(
            self.root, text="", font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=7, padx=10, pady=5, fg_color=self.game_theme.get("toast", "#172126"),
        )
        
        self.skin_cache = {} 
        self.apply_game_theme()

    def prune_destroyed_hotkey_buttons(self):
        """Forget widgets owned by a settings window already closed by Tk."""
        for key, button in list(self.hotkey_btns.items()):
            try:
                is_alive = bool(button.winfo_exists())
            except tk.TclError:
                is_alive = False
            if not is_alive:
                self.hotkey_btns.pop(key, None)
        alive_clear_buttons = []
        for button in self.hotkey_clear_buttons:
            try:
                is_alive = bool(button.winfo_exists())
            except tk.TclError:
                is_alive = False
            if is_alive:
                alive_clear_buttons.append(button)
        self.hotkey_clear_buttons = alive_clear_buttons

    def refresh_module_theme_images(self):
        """Reload the selected engine's background and banner textures."""
        image_name = self.game_theme.get("background_image")
        if not image_name:
            return
        path = resource_path("resources", "skin", image_name)
        if not os.path.exists(path):
            return
        self.wakfu_background_texture = self.create_rounded_theme_image(path, (670, 850), 18)
        self.wakfu_banner_texture = self.create_rounded_theme_image(path, (670, 58), 13)
        self.lbl_wakfu_background.configure(image=self.wakfu_background_texture)
        self.lbl_module_texture.configure(image=self.wakfu_banner_texture)

    @staticmethod
    def create_rounded_theme_image(path, size, radius):
        """Create an in-memory, alpha-masked background with genuinely rounded edges."""
        image = Image.open(path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255
        )
        image.putalpha(mask)
        return ctk.CTkImage(light_image=image, dark_image=image, size=size)

    def apply_game_theme(self):
        """Apply the visual module associated with the selected game engine."""
        self.prune_destroyed_hotkey_buttons()
        version = self.app.config.data.get("game_version", "Unity")
        theme = selected_game_theme(self.app.config.data)
        is_unity = version == "Unity"
        is_wakfu = version == "Wakfu"
        is_retro = version == "Rétro"
        has_module_theme = is_wakfu or is_retro or (is_unity and theme.get("module_surface", False))
        self.game_theme = theme
        if has_module_theme:
            self.refresh_module_theme_images()

        self.root.configure(fg_color=theme["background"])
        self.lbl_feedback.configure(fg_color=theme.get("toast", theme["panel"]))
        for frame in (
            self.frame_mode, self.frame_keys, self.frame_actions,
            self.frame_retro_layout, self.pill_frame, self.scroll_frame,
        ):
            frame.configure(
                fg_color=theme["panel"],
                border_width=1 if has_module_theme else 0,
                border_color=theme["border"] if has_module_theme else theme["panel"],
                corner_radius=13 if has_module_theme else 10,
            )
        self.header_f.configure(fg_color="transparent")
        self.lbl_app_title.configure(text_color=theme["title"])
        self.lbl_accounts.configure(text_color=theme["title"])
        self.lbl_controls.configure(text_color=theme["muted"])
        self.lbl_versions.configure(text_color=theme["muted"])
        self.lbl_keyboard_shortcuts.configure(text_color=theme["title"])
        self.lbl_retro_layout.configure(text_color=theme["title"])
        self.lbl_volume.configure(text_color=theme["muted"])
        self.btn_settings.configure(fg_color=theme["panel_alt"], hover_color=theme["accent"])
        self.btn_retro_autofocus_settings.configure(
            fg_color=theme["panel_alt"], hover_color=theme["accent_hover"],
            text_color=theme["title"], border_color=theme["border"],
        )
        for button in (self.btn_retro_maximize, self.btn_retro_tile):
            button.configure(
                fg_color=theme["accent"], hover_color=theme["accent_hover"],
                text_color=theme["title"], border_color=theme["border"],
            )
        self.btn_refresh.configure(fg_color=theme["accent"], hover_color=theme["accent_hover"])
        self.btn_sort_win.configure(fg_color=theme["panel_alt"], hover_color=theme["accent"])
        self.btn_manage_binds.configure(fg_color=theme["panel_alt"], hover_color=theme["accent"])
        for button in (
            self.btn_settings, self.btn_refresh, self.btn_sort_win,
            self.btn_manage_binds, self.btn_close_all, self.btn_reset,
        ):
            button.configure(corner_radius=10 if has_module_theme else 6)
        for button in self.hotkey_btns.values():
            button.configure(fg_color=theme["accent"], hover_color=theme["accent_hover"], corner_radius=10 if has_module_theme else 6)
        clear_color = theme.get("clear", "#c0392b") if has_module_theme else "#c0392b"
        clear_hover = theme.get("clear_hover", "#e74c3c") if has_module_theme else "#e74c3c"
        for button in self.hotkey_clear_buttons:
            button.configure(fg_color=clear_color, hover_color=clear_hover, corner_radius=10 if has_module_theme else 6)
        self.combo_mode.configure(
            fg_color=theme["accent"], button_color=theme["panel_alt"],
            button_hover_color=theme["accent_hover"],
        )
        self.update_autofocus_button()
        self.slider_volume.configure(progress_color=theme["accent"], button_color=theme["border"], button_hover_color=theme["title"])
        self.sw_character_bar.configure(
            progress_color=theme["accent"], button_color=theme["border"],
            button_hover_color=theme["accent_hover"], text_color=theme["title"],
        )
        self.frame_fast_command.configure(
            fg_color=theme["panel"], border_width=1 if has_module_theme else 0,
            border_color=theme["border"] if has_module_theme else theme["panel"],
            corner_radius=13 if has_module_theme else 8,
        )
        self.fast_invite_separator.configure(fg_color=theme["border"])
        for button in (self.btn_copy_fast_command, self.btn_copy_fast_invites):
            button.configure(fg_color=theme["accent"], hover_color=theme["accent_hover"], corner_radius=10 if has_module_theme else 6)
        for label in (
            self.lbl_fast_command, self.lbl_fast_invite,
            self.lbl_fast_command_value, self.lbl_fast_invite_value,
        ):
            label.configure(text_color=theme["title"])
        if has_module_theme:
            self.frame_module_banner.configure(
                fg_color=theme.get("banner", theme["panel"]), border_width=1, border_color=theme["border"]
            )
            self.lbl_module_title.configure(
                text="WAKFU" if is_wakfu else "DOFUS RÉTRO" if is_retro else "DOFUS UNITY"
            )
            self.lbl_module_subtitle.configure(text=ui_text(self.app, "group_management", "GESTION DE GROUPE"))
            self.lbl_module_title.configure(text_color=theme["title"])
            self.lbl_module_subtitle.configure(text_color=theme["muted"])
            self.lbl_wakfu_background.place(x=15, y=0)
            self.lbl_wakfu_background.lower()
            if not self.frame_module_banner.winfo_manager():
                self.frame_module_banner.pack(fill="x", padx=15, pady=(5, 6), before=self.frame_mode)
        else:
            self.frame_module_banner.pack_forget()
            self.lbl_wakfu_background.place_forget()
        bar = getattr(self.app, "character_bar", None)
        if bar:
            bar.update_theme(theme, version)
        self.update_version_selector(version)

    def apply_translations(self):
        self.prune_destroyed_hotkey_buttons()
        none_label = self.app.i18n.t("none", "Aucun")
        self.root.title(self.app.i18n.t("app_title", "DOSOFT v1.1.1"))
        self.lbl_app_title.configure(text=self.app.i18n.t("app_title", "DOSOFT v1.1.1"))
        self.root.title(APP_TITLE)
        self.lbl_app_title.configure(text=APP_TITLE)
        self.btn_settings.configure(text=self.app.i18n.t("header_settings", "⚙️ Paramètres"))
        self.btn_off.configure(text=self.app.i18n.t("header_off", "🔴 OFF"))
        self.lbl_controls.configure(text=self.app.i18n.t("label_controls", "Contrôler :"))
        self.lbl_versions.configure(text=self.app.i18n.t("label_versions", "Versions :"))
        self.lbl_keyboard_shortcuts.configure(text=self.app.i18n.t("label_keyboard_shortcuts", "Raccourcis Clavier"))
        self.lbl_volume.configure(text="")
        self.sw_character_bar.configure(text=ui_text(self.app, "character_bar", "Barre persos"))
        self.btn_close_all.configure(text=self.app.i18n.t("btn_close_team", "Fermer Team"))
        self.btn_reset.configure(text=self.app.i18n.t("btn_reset_settings", "Reset Settings"))
        self.lbl_accounts.configure(text=self.app.i18n.t("label_active_accounts", "Comptes actifs"))
        self.btn_refresh.configure(text=self.app.i18n.t("btn_refresh", "Rafraîchir"))
        self.btn_sort_win.configure(text=self.app.i18n.t("btn_sort_taskbar", "Trier Barre Windows"))
        self.chk_tooltips.configure(text=self.app.i18n.t("label_tooltips", "Bulles"))
        self.btn_hide.configure(text=self.app.i18n.t("btn_hide_ui", "Cacher l'UI"))
        self.lbl_module_subtitle.configure(text=ui_text(self.app, "group_management", "GESTION DE GROUPE"))
        self.lbl_retro_layout.configure(text=ui_text(self.app, "retro_windows_title", "Fenêtres Dofus Rétro"))
        self.btn_retro_maximize.configure(text=ui_text(self.app, "retro_windows_maximize", "▣ Agrandir tout"))
        self.btn_retro_tile.configure(text=ui_text(self.app, "retro_windows_tile", "▦ Ranger les fenêtres"))
        self.lbl_fast_command.configure(text=ui_text(self.app, "wakfu_follow_title", "Commande rapide"))
        self.lbl_fast_invite.configure(text=ui_text(self.app, "wakfu_invite_title", "Invitation de groupe"))
        self.btn_copy_fast_command.configure(text=ui_text(self.app, "copy", "Copier"))
        self.btn_copy_fast_invites.configure(text=ui_text(self.app, "copy", "Copier"))
        self.chk_autofocus.configure(text="")
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

    def update_obs_quick_controls(self):
        if self.app.obs_bridge.enabled:
            if not self.obs_quick_frame.winfo_manager():
                self.obs_quick_frame.pack(side="right", padx=(8, 6), pady=3)
            if hasattr(self, "lbl_obs_connection") and not self.lbl_obs_connection.winfo_manager():
                self.lbl_obs_connection.pack(side="right", padx=(0, 6))
        else:
            self.obs_quick_frame.pack_forget()
            if hasattr(self, "lbl_obs_connection"):
                self.lbl_obs_connection.pack_forget()

    def poll_obs_connection_badge(self):
        snapshot = self.app.obs_bridge.status_snapshot()
        connected_badge = (
            (f"● OBS {snapshot['plugin_version'] or ''} ⚠".rstrip(), "#a8611a")
            if snapshot.get("compatibility_warnings") else
            (f"● OBS {snapshot['plugin_version'] or ''}".rstrip(), "#267a45")
        )
        states = {
            "connected": connected_badge,
            "connecting": ("● OBS…", "#8a6d1d"),
            "disconnected": (ui_text(self.app, "obs_badge_disconnected", "● OBS déconnecté"), "#a62020"),
            "degraded": (ui_text(self.app, "obs_badge_check", "● OBS à vérifier"), "#a8611a"),
            "incompatible": (ui_text(self.app, "obs_badge_incompatible", "● OBS incompatible"), "#8f1d2c"),
            "profile_required": (ui_text(self.app, "obs_badge_configure", "● OBS à configurer"), "#76559a"),
            "disabled": ("", "transparent"),
        }
        text, color = states.get(snapshot["state"], ("● OBS ?", "#59606b"))
        self.lbl_obs_connection.configure(text=text, fg_color=color, text_color="#ffffff")
        if self.app.obs_bridge.enabled:
            if not self.lbl_obs_connection.winfo_manager():
                self.lbl_obs_connection.pack(side="right", padx=(0, 6))
        else:
            self.lbl_obs_connection.pack_forget()
        try:
            self.root.after(500, self.poll_obs_connection_badge)
        except tk.TclError:
            pass

    def open_obs_extension(self):
        if not self.app.obs_bridge.enabled:
            return
        settings = getattr(self, "settings_window", None)
        if settings is not None and settings.winfo_exists():
            settings.attributes("-topmost", False)
            settings.lower()
        window = getattr(self, "obs_settings_window", None)
        if window is None or not window.winfo_exists():
            self.obs_settings_window = ObsSettingsWindow(self)
        else:
            window.show_foreground()

    def emergency_restart_obs(self):
        if not self.app.obs_bridge.enabled:
            return
        confirmed = messagebox.askyesno(
            ui_text(self.app, "obs_emergency_title", "Redémarrage d'urgence OBS"),
            ui_text(
                self.app, "obs_emergency_confirm",
                "OBS va supprimer toutes les captures Dofus gérées par DOSOFT puis les recréer à partir des personnages actuellement détectés.\n\nContinuer ?",
            ),
            parent=self.root,
        )
        if not confirmed:
            return
        self.show_temporary_message(ui_text(self.app, "obs_emergency_progress", "Actualisation de DOSOFT et reconstruction des captures OBS…"), "#f0b429")

        response_holder = {"value": None}

        def completed(response):
            response_holder["value"] = response

        def poll_response():
            response = response_holder["value"]
            if response is None:
                self.root.after(100, poll_response)
                return
            if response.get("ok"):
                self.show_temporary_message(ui_text(self.app, "obs_emergency_success", "Captures OBS recréées avec succès."), "#67d391")
            elif response.get("error") == "no_ready_accounts":
                self.show_temporary_message(ui_text(self.app, "obs_emergency_no_accounts", "Aucun personnage Dofus prêt : reconstruction annulée."), "#f0b429")
            else:
                self.show_temporary_message(ui_text(self.app, "obs_emergency_failed", "OBS n'a pas pu reconstruire les captures."), "#e05b5b")

        self.app.rebuild_obs_team(completed)
        self.root.after(100, poll_response)

    def toggle_from_tray(self, icon, item):
        """ Demande à l'interface de s'afficher ou de se cacher proprement """
        self.gui.root.after(0, self.gui.toggle_visibility)

    def show_temporary_message(self, text, color="#2ecc71"):
        self.lbl_feedback.configure(text=text, text_color=color)
        self.lbl_feedback.place(relx=0.5, rely=0.82, anchor="center")
        if hasattr(self, "feedback_timer"):
            self.root.after_cancel(self.feedback_timer)
        self.feedback_timer = self.root.after(2500, self.lbl_feedback.place_forget)

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
        confirmed = messagebox.askyesno(
            ui_text(self.app, "close_account_title", "Fermer un compte"),
            ui_text(self.app, "close_account_confirm", "Demander à la fenêtre « {name} » de se fermer proprement ?", name=name),
            parent=self.root,
        )
        if not confirmed:
            return
        if self.app.logic.close_account_window(name):
            self.show_temporary_message(ui_text(self.app, "close_account_requested", "Fermeture demandée pour {name}.", name=name), "#f0b429")
            self.root.after(900, self.original_app_refresh)
        else:
            self.show_temporary_message(ui_text(self.app, "close_account_failed", "Impossible de fermer {name}.", name=name), "#e05b5b")
        
    def close_all_and_refresh(self):
        count = len(self.app.logic.get_cycle_list())
        if not count:
            self.show_temporary_message(ui_text(self.app, "close_team_empty", "Aucun compte actif à fermer."), "#f0b429")
            return
        confirmed = messagebox.askyesno(
            ui_text(self.app, "close_team_title", "Fermer la team"),
            ui_text(
                self.app, "close_team_confirm",
                "Demander la fermeture propre de {count} fenêtre(s) de jeu ?\n\nChaque jeu pourra enregistrer ses paramètres avant de quitter.", count=count,
            ),
            parent=self.root,
        )
        if not confirmed:
            return
        requested = self.app.logic.close_all_active_accounts()
        self.show_temporary_message(
            ui_text(self.app, "close_team_requested", "Fermeture demandée pour {count} fenêtre(s).", count=requested), "#e74c3c"
        )
        self.root.after(1200, self.original_app_refresh)

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

    def toggle_team_ui(self, name, btn):
        current_team = self.app.config.data.get("accounts_team", {}).get(name, "Team 1")
        new_team = "Team 2" if current_team == "Team 1" else "Team 1"
        self.app.logic.change_team(name, new_team)
        team_color = "#2980b9" if new_team == "Team 1" else "#c0392b"
        btn.configure(text="T1" if new_team == "Team 1" else "T2", fg_color=team_color)
        self.refresh_list(self.app.logic.all_accounts, self.app.config.data.get("game_version", "Unity"))

    def refresh_list(self, accounts, source_version=None):
        # Ignore a delayed scan whose source engine was changed in the meantime.
        if source_version and source_version != self.app.config.data.get("game_version", "Unity"):
            return
        bar = getattr(self.app, "character_bar", None)
        if bar:
            bar.update_accounts(accounts, self.app.config.data.get("game_version", "Unity"))
        self.update_fast_command(accounts)
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        leader_name = self.app.config.data.get("leader_name", "")
        
        game_version = self.app.config.data.get("game_version", "Unity")
        is_retro = game_version == "Rétro"
        uses_manual_classes = game_version in ("Rétro", "Wakfu")
        # Correspond exactement aux portraits disponibles dans resources/skin/retro.
        # « Inconnu » est conservé pour le Menu Rétro / les fenêtres non détectées.
        retro_manual_classes = [
            "Inconnu", "Feca", "Osamodas", "Enutrof", "Sram", "Xelor", "Ecaflip",
            "Eniripsa", "Iop", "Cra", "Sadida", "Sacrieur", "Pandawa",
        ]
        wakfu_manual_classes = [
            "Inconnu", "Feca", "Osamodas", "Enutrof", "Sram", "Xelor", "Ecaflip",
            "Eniripsa", "Iop", "Cra", "Sadida", "Sacrieur", "Pandawa", "Roublard",
            "Zobal", "Steamer", "Eliotrope", "Huppermage", "Ouginak", "Belaphon",
        ]
        manual_classes = retro_manual_classes if is_retro else wakfu_manual_classes
        
        for idx, acc in enumerate(accounts):
            row_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            
            class_engine = "retro" if is_retro else "wakfu" if game_version == "Wakfu" else "unity"
            img = self.get_class_image(acc.get('classe', 'Inconnu'), class_engine)
            if img: ctk.CTkLabel(row_frame, image=img, text="").pack(side="left", padx=5)
            else: ctk.CTkLabel(row_frame, text="👤").pack(side="left", padx=5) 
            
            var = tk.BooleanVar(value=acc['active'])
            
            chk_width = 110 if is_retro else 160
            account_display_name = acc['name'] if acc.get('is_menu') else acc['name'][:15]
            chk = ctk.CTkCheckBox(
                row_frame,
                text=account_display_name,
                variable=var,
                width=chk_width,
                command=lambda n=acc['name'], v=var: self.toggle_account_from_ui(n, v.get()),
            )
            chk.pack(side="left", padx=(5, 0))

            if uses_manual_classes:
                combo_classe = ctk.CTkOptionMenu(
                    row_frame, 
                    values=manual_classes,
                    width=90, height=24,
                    fg_color="#34495e", button_color="#2c3e50", button_hover_color="#1a252f",
                    command=lambda val, n=acc['name']: self.change_manual_class(n, val)
                )
                combo_classe.set(acc.get('classe', 'Inconnu'))
                combo_classe.pack(side="left", padx=5)

            btn_close = ctk.CTkButton(row_frame, text="✖", width=25, fg_color="#c0392b", hover_color="#e74c3c")
            btn_close.configure(command=lambda n=acc['name']: self.close_and_refresh(n))
            btn_close.pack(side="right", padx=(2, 5))
            self.bind_i18n_tooltip(btn_close, "tooltip_close_game", "Fermer instantanément le jeu")
            
            is_leader = (acc['name'] == leader_name)
            leader_txt = "🌟" if is_leader else "☆"
            leader_color = "#f39c12" if is_leader else "transparent"
            btn_lead = ctk.CTkButton(row_frame, text=leader_txt, width=35, fg_color=leader_color, border_width=1, command=lambda n=acc['name']: self.set_leader(n))
            btn_lead.pack(side="right", padx=2)
            self.bind_i18n_tooltip(btn_lead, "tooltip_set_leader", "Définir comme Chef")

            team_val = acc.get('team', "Team 1")
            team_color = "#2980b9" if team_val == "Team 1" else "#c0392b"
            btn_team = ctk.CTkButton(row_frame, text="T1" if team_val == "Team 1" else "T2", width=35, fg_color=team_color)
            btn_team.configure(command=lambda n=acc['name'], b=btn_team: self.toggle_team_ui(n, b))
            btn_team.pack(side="right", padx=5)
            self.bind_i18n_tooltip(btn_team, "tooltip_change_team", "Changer d'équipe (T1/T2)")

            btn_down = ctk.CTkButton(row_frame, text="▼", width=25, fg_color="#34495e", hover_color="#2c3e50")
            btn_down.configure(command=lambda n=acc['name']: self.move_row(n, 1))
            btn_down.pack(side="right", padx=(2, 10))
            self.bind_i18n_tooltip(btn_down, "tooltip_move_down", "Descendre dans l'initiative")
            
            btn_up = ctk.CTkButton(row_frame, text="▲", width=25, fg_color="#34495e", hover_color="#2c3e50")
            btn_up.configure(command=lambda n=acc['name']: self.move_row(n, -1))
            btn_up.pack(side="right", padx=2)
            self.bind_i18n_tooltip(btn_up, "tooltip_move_up", "Monter dans l'initiative")

            pos_values = [str(i+1) for i in range(len(accounts))]
            current_pos = str(idx + 1)
            combo_pos = ctk.CTkOptionMenu(row_frame, values=pos_values, width=50, height=24, fg_color="#34495e", button_color="#2c3e50", button_hover_color="#1a252f")
            combo_pos.set(current_pos)
            combo_pos.configure(command=lambda val, n=acc['name']: self.change_position(n, val))
            combo_pos.pack(side="right", padx=(2, 5))
            self.bind_i18n_tooltip(combo_pos, "tooltip_exact_position", "Choisir la position exacte")

    def _autofocus_config_key(self):
        return "auto_focus_retro"

    def toggle_autofocus(self):
        self.var_autofocus.set(not self.var_autofocus.get())
        self.app.set_retro_autofocus_enabled(self.var_autofocus.get())
        self.update_autofocus_button()

    def maximize_retro_windows(self):
        result = self.app.logic.maximize_retro_windows()
        if not result.requested:
            self.show_temporary_message(ui_text(self.app, "retro_windows_none", "Aucune fenêtre Dofus Rétro détectée."), "#f0b429")
        elif result.failed:
            self.show_temporary_message(
                ui_text(self.app, "retro_windows_maximize_partial", "{changed} fenêtre(s) agrandie(s), {failed} échec(s).", changed=result.changed, failed=result.failed),
                "#f0b429",
            )
        else:
            self.show_temporary_message(
                ui_text(self.app, "retro_windows_maximize_success", "{count} fenêtre(s) Rétro agrandie(s).", count=result.changed), "#67d391"
            )

    def tile_retro_windows(self):
        result = self.app.logic.tile_retro_windows()
        if not result.requested:
            self.show_temporary_message(ui_text(self.app, "retro_windows_none", "Aucune fenêtre Dofus Rétro détectée."), "#f0b429")
        elif result.failed:
            self.show_temporary_message(
                ui_text(self.app, "retro_windows_tile_partial", "{changed} fenêtre(s) rangée(s), {failed} échec(s).", changed=result.changed, failed=result.failed),
                "#f0b429",
            )
        else:
            self.show_temporary_message(
                ui_text(self.app, "retro_windows_tile_success", "{count} fenêtre(s) Rétro rangée(s) sur l’écran.", count=result.changed), "#67d391"
            )

    def open_retro_autofocus_settings(self):
        window = self.retro_autofocus_settings_window
        if window is not None and window.winfo_exists():
            window.deiconify()
            window.lift()
            window.focus_force()
            return
        self.retro_autofocus_settings_window = RetroAutofocusSettingsWindow(self)

    def update_autofocus_button(self):
        """Render the image-only autofocus switch with the selected-game outline."""
        theme = getattr(self, "game_theme", GAME_THEMES["Unity"])
        active = self.var_autofocus.get()
        self.chk_autofocus.configure(
            fg_color=theme["accent"] if active else theme["panel_alt"],
            hover_color=theme["accent_hover"],
            border_width=2 if active else 0,
            border_color=theme["border"] if active else theme["panel_alt"],
        )
        
    def on_volume_change(self, value): self.app.update_volume(int(value))

    def toggle_character_bar(self):
        self.app.set_character_bar_visible(self.var_character_bar.get())
    
    def create_hotkey_row(self, parent, label_key, config_key, row, col_offset, tooltip_key=""):
        lbl = ctk.CTkLabel(parent, text=f"{self.app.i18n.t(label_key, label_key)}:")
        lbl.grid(row=row, column=col_offset, padx=5, sticky="w")
        if tooltip_key:
            self.bind_i18n_tooltip(lbl, tooltip_key, tooltip_key)
        self.hotkey_labels[config_key] = (lbl, label_key)
        
        current_val = self.app.config.data.get(config_key, "")
        theme = getattr(self, "game_theme", GAME_THEMES["Unity"])
        btn = ctk.CTkButton(
            parent, text=current_val if current_val else self.app.i18n.t("none", "Aucun"),
            width=80, fg_color=theme["accent"], hover_color=theme["accent_hover"],
            command=lambda: self.catch_key(config_key, btn, allow_mouse=True),
        )
        btn.grid(row=row, column=col_offset+1, padx=2, pady=2)
        
        self.hotkey_btns[config_key] = btn 
        
        is_module_theme = self.app.config.data.get("game_version") in ("Unity", "Wakfu", "Rétro")
        theme = getattr(self, "game_theme", GAME_THEMES["Unity"])
        btn_x = ctk.CTkButton(
            parent, text="✖", width=25,
            fg_color=theme.get("clear", "#c0392b") if is_module_theme else "#c0392b",
            hover_color=theme.get("clear_hover", "#e74c3c") if is_module_theme else "#e74c3c",
            command=lambda: self.clear_key(config_key, btn),
        )
        btn_x.grid(row=row, column=col_offset+2, padx=(0, 10))
        self.hotkey_clear_buttons.append(btn_x)
        self.bind_i18n_tooltip(btn_x, "tooltip_clear_shortcut", "Effacer le raccourci")

    def catch_key(self, config_key, btn, allow_mouse=False):
        if self.is_listening:
            write_hotkey_debug(f"CAPTURE_IGNORED key={config_key} reason=already_listening")
            return

        previous_value = self.app.config.data.get(config_key, "")
        try:
            mods_now = []
            if win32api.GetAsyncKeyState(win32con.VK_CONTROL) < 0: mods_now.append("ctrl")
            if win32api.GetAsyncKeyState(win32con.VK_MENU) < 0: mods_now.append("alt")
            if win32api.GetAsyncKeyState(win32con.VK_SHIFT) < 0: mods_now.append("shift")
            self.is_listening = True
            self.app.hotkey_capture_active = True
            btn.configure(text="(...)", fg_color="#f39c12")
            write_hotkey_debug(
                f"CAPTURE_START key={config_key} previous={previous_value!r} mouse={allow_mouse}"
            )
            threading.Thread(
                target=self._listen_hotkey_thread,
                args=(config_key, btn, allow_mouse, mods_now),
                daemon=True,
            ).start()
        except Exception as exc:
            self.is_listening = False
            self.app.hotkey_capture_active = False
            write_hotkey_debug(f"CAPTURE_START_ERROR key={config_key} error={exc!r}", "exception")
            try:
                btn.configure(text=previous_value or self.app.i18n.t("none", "Aucun"))
            except Exception:
                pass

    def _listen_hotkey_thread(self, config_key, btn, allow_mouse, mods_before_click=None):
        if mods_before_click is None: mods_before_click = []
        captured_key = None
        captured_mods = []
        hook = None
        capture_error = None

        def get_current_mods():
            mods = []
            if win32api.GetAsyncKeyState(win32con.VK_CONTROL) < 0: mods.append("ctrl")
            if win32api.GetAsyncKeyState(win32con.VK_MENU) < 0: mods.append("alt")
            if win32api.GetAsyncKeyState(win32con.VK_SHIFT) < 0: mods.append("shift")
            return mods

        # Never wait forever for a mouse button which Windows or a driver still
        # reports as held. This was able to leave shortcut capture armed.
        release_deadline = time.monotonic() + 2.0
        while ((win32api.GetAsyncKeyState(win32con.VK_LBUTTON) < 0
                or win32api.GetAsyncKeyState(win32con.VK_RBUTTON) < 0
                or win32api.GetAsyncKeyState(win32con.VK_MBUTTON) < 0
                or win32api.GetAsyncKeyState(0x05) < 0
                or win32api.GetAsyncKeyState(0x06) < 0)
               and time.monotonic() < release_deadline):
            time.sleep(0.01)
        time.sleep(0.1)
        deadline = time.monotonic() + 10.0

        held_mods = set(mods_before_click)
        mod_names = {'alt', 'ctrl', 'shift', 'maj', 'right alt', 'right ctrl',
                     'left alt', 'left ctrl', 'left shift', 'right shift',
                     'alt gr', 'menu', 'windows', 'cmd', 'left windows', 'right windows'}
        mod_map = {'alt': 'alt', 'left alt': 'alt', 'right alt': 'alt', 'menu': 'alt',
                   'ctrl': 'ctrl', 'left ctrl': 'ctrl', 'right ctrl': 'ctrl',
                   'shift': 'shift', 'left shift': 'shift', 'right shift': 'shift',
                   'maj': 'shift'}

        def on_key(event):
            nonlocal captured_key, captured_mods
            if event.name in mod_map:
                if event.event_type == keyboard.KEY_DOWN:
                    held_mods.add(mod_map[event.name])
                elif event.event_type == keyboard.KEY_UP:
                    held_mods.discard(mod_map[event.name])
                return
            if event.event_type == keyboard.KEY_DOWN and event.name not in mod_names:
                captured_mods = [m for m in ['ctrl', 'alt', 'shift'] if m in held_mods]
                captured_key = self.app.keymaps.scan_to_key_name(event.scan_code) or event.name

        try:
            # Do not suppress system-wide input while listening. A failed hook
            # must never make Windows controls unusable.
            hook = keyboard.hook(on_key, suppress=False)
            while not captured_key and time.monotonic() < deadline:
                if allow_mouse:
                    if win32api.GetAsyncKeyState(win32con.VK_LBUTTON) < 0: captured_key = "left_click"
                    elif win32api.GetAsyncKeyState(win32con.VK_RBUTTON) < 0: captured_key = "right_click"
                    elif win32api.GetAsyncKeyState(win32con.VK_MBUTTON) < 0: captured_key = "middle_click"
                    elif win32api.GetAsyncKeyState(0x05) < 0: captured_key = "mouse4"
                    elif win32api.GetAsyncKeyState(0x06) < 0: captured_key = "mouse5"
                    if captured_key:
                        captured_mods = [m for m in ['ctrl', 'alt', 'shift'] if m in held_mods]
                time.sleep(0.01)
        except Exception as exc:
            capture_error = repr(exc)
            write_hotkey_debug(
                f"CAPTURE_LISTEN_ERROR key={config_key} error={capture_error}", "exception"
            )
        finally:
            if hook is not None:
                try:
                    keyboard.unhook(hook)
                except Exception:
                    pass

        if not captured_key or captured_key == "esc":
            final_key = self.app.config.data.get(config_key, "")
        else:
            final_key = "+".join(captured_mods) + "+" + captured_key if captured_mods else captured_key

        write_hotkey_debug(
            f"CAPTURE_RESULT key={config_key} captured={captured_key!r} "
            f"final={final_key!r} error={capture_error}"
        )
        try:
            self.root.after(
                0, self.finish_hotkey_capture, config_key, final_key, btn, capture_error
            )
        except Exception as exc:
            # The window may be closing. Never leave the application suspended.
            self.is_listening = False
            self.app.hotkey_capture_active = False
            write_hotkey_debug(f"CAPTURE_UI_ERROR key={config_key} error={exc!r}", "exception")

    def finish_hotkey_capture(self, config_key, final_key, btn, capture_error=None):
        # Resume normal hooks before apply_single_hotkey rebuilds them.
        self.is_listening = False
        self.app.hotkey_capture_active = False
        try:
            if capture_error:
                previous_value = self.app.config.data.get(config_key, "")
                theme = getattr(self, "game_theme", GAME_THEMES["Unity"])
                btn.configure(
                    text=previous_value or self.app.i18n.t("none", "Aucun"),
                    fg_color=theme["accent"], hover_color=theme["accent_hover"],
                )
                return
            self.apply_single_hotkey(config_key, final_key, btn)
        finally:
            self.is_listening = False
            self.app.hotkey_capture_active = False
            write_hotkey_debug(f"CAPTURE_END key={config_key}")

    def release_modifiers(self):
        try:
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
        except: pass

    def apply_single_hotkey(self, config_key, new_value, btn):
        self.prune_destroyed_hotkey_buttons()
        new_value = normalize_hotkey(new_value)
        conflict = assignment_conflict(self.app.config.data, config_key, new_value)
        if conflict:
            previous = self.app.config.data.get(config_key, "")
            messagebox.showwarning(
                ui_text(self.app, "hotkey_already_used_title", "Raccourci déjà utilisé"),
                ui_text(
                    self.app, "hotkey_already_used_message",
                    "{hotkey} est déjà associé à « {action} ».\n\nChoisissez une autre touche afin que chaque action reste prévisible.",
                    hotkey=new_value.upper(), action=conflict,
                ),
                parent=self.root,
            )
            theme = getattr(self, "game_theme", GAME_THEMES["Unity"])
            btn.configure(
                text=previous or self.app.i18n.t("none", "Aucun"),
                fg_color=theme["accent"], hover_color=theme["accent_hover"],
            )
            return False

        self.app.config.data[config_key] = new_value
        if not self.app.config.save():
            return False
        
        theme = getattr(self, "game_theme", GAME_THEMES["Unity"])
        btn.configure(
            text=new_value if new_value else self.app.i18n.t("none", "Aucun"),
            fg_color=theme["accent"], hover_color=theme["accent_hover"],
        )
        self.app.setup_hotkeys()
        self.is_listening = False
        return True

    def clear_key(self, config_key, btn):
        if self.is_listening: return
        self.apply_single_hotkey(config_key, "", btn)

    def on_version_change(self, choice):
        if choice == self.app.config.data.get("game_version", "Unity"):
            return
        self.app.change_game_engine(choice)
        self.apply_game_theme()
        self.update_version_selector(choice)
        self.var_autofocus.set(
            self.app.config.data.get("auto_focus_retro", False) if choice == "Rétro" else False
        )
        self.update_autofocus_button()
        if choice == "Rétro":
            self.chk_autofocus.pack(side="left", padx=(15, 5))
        else:
            self.chk_autofocus.pack_forget()
        if choice == "Rétro":
            self.btn_retro_autofocus_settings.pack(side="left", padx=(0, 5))
            if not self.frame_retro_layout.winfo_manager():
                self.frame_retro_layout.pack(
                    fill="x", padx=15, pady=(0, 5), after=self.frame_mode
                )
        else:
            self.btn_retro_autofocus_settings.pack_forget()
            self.frame_retro_layout.pack_forget()
            window = self.retro_autofocus_settings_window
            if window is not None and window.winfo_exists():
                window.close()
        self.original_app_refresh()
        self.show_temporary_message(self.app.i18n.t("msg_mode_enabled", "🔄 Mode {choice} activé !").format(choice=choice), "#3498db")

    def on_mode_change(self, choice):
        # Changing the filter does not alter the account rows. Updating the
        # quick bar directly avoids destroying/recreating the whole main UI.
        self.app.set_team_mode(choice)

    def toggle_account_from_ui(self, name, is_active):
        """Keep the quick character bar in sync with a row checkbox."""
        self.app.logic.toggle_account(name, is_active)
        self.refresh_list(self.app.logic.all_accounts, self.app.config.data.get("game_version", "Unity"))

    def load_selector_image(self, icon_name, size=(28, 28)):
        path = resource_path("resources", "skin", f"{icon_name}.png")
        if not os.path.exists(path):
            return None
        image = Image.open(path)
        return ctk.CTkImage(light_image=image, dark_image=image, size=size)

    def update_version_selector(self, selected_version):
        theme = getattr(self, "game_theme", GAME_THEMES["Unity"])
        for version, button in self.version_buttons.items():
            is_selected = version == selected_version
            button.configure(
                fg_color=theme["accent"] if is_selected else theme["panel_alt"],
                hover_color=theme["accent_hover"] if is_selected else theme["panel"],
                border_width=2 if is_selected else 0,
                border_color=theme["border"] if is_selected else theme["panel_alt"],
            )

    def get_class_image(self, class_name, engine="unity"):
        cache_key = f"{engine}:{class_name}"
        if cache_key in self.skin_cache: return self.skin_cache[cache_key]
        path = skin_path(class_name, engine=engine)
        if not os.path.exists(path): return None
        img = ctk.CTkImage(light_image=Image.open(path), dark_image=Image.open(path), size=(24, 24))
        self.skin_cache[cache_key] = img
        return img

    def change_manual_class(self, name, new_class):
        self.app.config.data["classes"][name] = new_class
        self.app.config.save()
        self.original_app_refresh()

    def set_leader(self, name):
        self.app.logic.set_leader(name)
        self.original_app_refresh()

    def update_fast_command(self, accounts=None):
        """Show one-click WAKFU follow and group-invite commands."""
        is_wakfu = self.app.config.data.get("game_version") == "Wakfu"
        if not is_wakfu:
            self.frame_fast_command.pack_forget()
            return

        # Réserve sa hauteur avant que le panneau de comptes ne prenne l'espace
        # extensible : les deux commandes restent toujours entièrement visibles.
        if self.frame_fast_command.winfo_manager():
            self.frame_fast_command.pack_forget()
        self.frame_fast_command.pack(
            fill="x", padx=15, pady=(0, 6), before=self.frame_footer
        )

        leader_name = self.app.config.data.get("leader_name", "").strip()
        if leader_name:
            self.fast_command = f"/follow {leader_name}"
            self.lbl_fast_command_value.configure(text=self.fast_command, font=ctk.CTkFont(weight="bold"))
            self.btn_copy_fast_command.configure(state="normal")
            characters = accounts if accounts is not None else self.app.logic.all_accounts
            invitees = [
                account["name"] for account in characters
                if account["name"] != leader_name and not account.get("is_menu", False)
            ]
            self.fast_invite_commands = "\n".join(f"/invite {pseudo}" for pseudo in invitees)
            if self.fast_invite_commands:
                self.lbl_fast_invite_value.configure(
                    text="  |  ".join(self.fast_invite_commands.splitlines()),
                    font=ctk.CTkFont(weight="bold"),
                )
                self.btn_copy_fast_invites.configure(state="normal")
            else:
                self.lbl_fast_invite_value.configure(
                    text=ui_text(self.app, "wakfu_no_other_character", "Aucun autre personnage détecté."), font=ctk.CTkFont()
                )
                self.btn_copy_fast_invites.configure(state="disabled")
        else:
            self.fast_command = ""
            self.fast_invite_commands = ""
            self.lbl_fast_command_value.configure(
                text=ui_text(self.app, "wakfu_follow_no_leader", "Définis un meneur pour générer la commande."), font=ctk.CTkFont()
            )
            self.btn_copy_fast_command.configure(state="disabled")
            self.lbl_fast_invite_value.configure(
                text=ui_text(self.app, "wakfu_invite_no_leader", "Définis un meneur pour générer les invitations."), font=ctk.CTkFont()
            )
            self.btn_copy_fast_invites.configure(state="disabled")

    def copy_fast_command(self):
        if not getattr(self, "fast_command", ""):
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.fast_command)
        self.root.update()
        self.show_temporary_message(ui_text(self.app, "wakfu_follow_copied", "✅ Commande /follow copiée."), "#2ecc71")

    def copy_fast_invites(self):
        if not getattr(self, "fast_invite_commands", ""):
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.fast_invite_commands)
        self.root.update()
        self.show_temporary_message(ui_text(self.app, "wakfu_invites_copied", "✅ Commandes /invite copiées."), "#2ecc71")

    def reset_all(self):
        reponse = messagebox.askyesno(
            self.app.i18n.t("dialog_confirm_title", "Confirmation"),
            ui_text(
                self.app, "reset_full_confirm",
                "Réinitialiser entièrement DOSOFT ?\n\nLes raccourcis, équipes, thèmes et le profil OBS seront remis à zéro. Les sauvegardes d’affichage Dofus ne seront pas supprimées.",
            ),
            parent=self.root,
        )
        if reponse:
            ok, error = self.app.reset_to_defaults()
            if not ok:
                messagebox.showerror(ui_text(self.app, "reset_title", "Réinitialisation DOSOFT"), error, parent=self.root)
                return
            settings = getattr(self, "settings_window", None)
            if settings is not None and settings.winfo_exists():
                settings.destroy()
            obs_settings = getattr(self, "obs_settings_window", None)
            if obs_settings is not None and obs_settings.winfo_exists():
                obs_settings.destroy()
            self.combo_mode.set("ALL")
            self.slider_volume.set(50)
            self.var_character_bar.set(False)
            self.var_tooltips.set(True)
            self.var_autofocus.set(False)
            self.chk_autofocus.pack_forget()
            self.btn_retro_autofocus_settings.pack_forget()
            self.frame_retro_layout.pack_forget()
            self.update_version_selector("Unity")
            self.update_obs_quick_controls()
            self.apply_game_theme()
            self.apply_translations()
            self.original_app_refresh()
            self.show_temporary_message(ui_text(self.app, "reset_success", "DOSOFT a été entièrement réinitialisé."), "#2ecc71")

    def hide_to_tray(self):
        """ Cache la fenêtre quand on clique sur la croix, sans la détruire """
        self.root.withdraw()
        self.is_visible = False

    def toggle_visibility(self):
        """ Alterne entre l'affichage et la mise en veille dans la barre des tâches """
        if self.is_visible:
            self.hide_to_tray()
        else:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force() # Force la fenêtre à passer par-dessus les autres !
            self.is_visible = True

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
        close_context_when_clicked_outside(self)

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

        hook = None
        deadline = time.monotonic() + 10.0
        try:
            hook = keyboard.hook(on_key, suppress=False)
            while not captured and time.monotonic() < deadline:
                if win32api.GetAsyncKeyState(0x05) < 0: captured = "mouse4"
                elif win32api.GetAsyncKeyState(0x06) < 0: captured = "mouse5"
                elif win32api.GetAsyncKeyState(0x04) < 0: captured = "middle_click"
                time.sleep(0.01)
        finally:
            if hook is not None:
                try:
                    keyboard.unhook(hook)
                except Exception:
                    pass
            self.parent.release_modifiers()
        if not captured:
            captured = self.entry_dict.get(dict_key, "")
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

            game_version = self.app.config.data.get("game_version", "Unity")
            class_engine = "retro" if game_version == "Rétro" else "wakfu" if game_version == "Wakfu" else "unity"
            for acc in active_list:
                pseudo = acc['name']
                frame_row = ctk.CTkFrame(self.scroll_list)
                frame_row.pack(fill="x", pady=2, padx=5)
                
                img = self.parent.get_class_image(acc.get('classe', 'Inconnu'), class_engine)
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
        candidate = deepcopy(cfg)
        candidate["advanced_bind_modifier"] = mod_prefix
        
        if mode == "cycle":
            new_binds = []
            for i in range(8):
                base = self.entry_dict.get(i, "").lower().strip()
                new_binds.append(prefix_str + base if base else "")
            candidate["cycle_row_binds"] = new_binds
            candidate["advanced_bind_mode"] = "cycle"

        elif mode == "bind":
            character_binds = dict(candidate.get("persistent_character_binds", {}))
            for pseudo, base in self.entry_dict.items():
                base = base.lower().strip()
                character_binds[pseudo] = prefix_str + base if base else ""
            candidate["persistent_character_binds"] = character_binds
            candidate["advanced_bind_mode"] = "bind"

        conflicts = find_hotkey_conflicts(candidate)
        if conflicts:
            messagebox.showwarning(
                ui_text(self.app, "hotkey_conflict_title", "Conflit de raccourcis"),
                ui_text(
                    self.app, "hotkey_conflict_save_message",
                    "Impossible d’enregistrer : certaines actions utilisent la même touche.\n\n{details}",
                    details=describe_conflicts(conflicts),
                ),
                parent=self,
            )
            return

        cfg.update(candidate)
        if not self.app.config.save():
            return
        self.parent.show_temporary_message(self.app.i18n.t("msg_binds_saved", "✅ Raccourcis enregistrés avec succès !"), "#2ecc71")
        self.app.setup_hotkeys() 
        self.destroy()
