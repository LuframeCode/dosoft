import tkinter as tk
import os
from PIL import Image, ImageTk

CLASSE_TO_SKIN = {
    "cra": "skin/cra.png",
    "ecaflip": "skin/ecaflip.png",
    "eliotrope": "skin/eliotrope.png",
    "eniripsa": "skin/eniripsa.png",
    "enutrof": "skin/enutrof.png",
    "feca": "skin/feca.png",
    "forgelance": "skin/forgelance.png",
    "huppermage": "skin/huppermage.png",
    "iop": "skin/iop.png",
    "osamodas": "skin/osamodas.png",
    "ouginak": "skin/ouginak.png",
    "pandawa": "skin/pandawa.png",
    "roublard": "skin/roublard.png",
    "sacrieur": "skin/sacrieur.png",
    "sadida": "skin/sadida.png",
    "sram": "skin/sram.png",
    "steamer": "skin/steamer.png",
    "xelor": "skin/xelor.png",
    "zobal": "skin/zobal.png",
    # Rétro variants
    "cra_retro": "skin/cra_retro.png",
    "ecaflip_retro": "skin/ecaflip_retro.png",
    "eniripsa_retro": "skin/eniripsa_retro.png",
    "enutrof_retro": "skin/enutrof_retro.png",
    "feca_retro": "skin/feca_retro.png",
    "iop_retro": "skin/iop_retro.png",
    "osamodas_retro": "skin/osamodas_retro.png",
    "pandawa_retro": "skin/pandawa_retro.png",
    "sacrieur_retro": "skin/sacrieur_retro.png",
    "sadida_retro": "skin/sadida_retro.png",
    "sram_retro": "skin/sram_retro.png",
    "xelor_retro": "skin/xelor_retro.png",
}

BG_COLOR = "#1a1a2e"
ACTIVE_COLOR = "#2ecc71"
INACTIVE_COLOR = "#2c3e50"
HOVER_COLOR = "#34495e"
TEXT_COLOR = "#ecf0f1"
SUBTEXT_COLOR = "#95a5a6"
BTN_SIZE = 64      # width per account button
BAR_HEIGHT = 72    # total bar height
ICON_SIZE = 36


def get_account_icon_path(name, classe, config):
    custom = config.data.get("account_icons", {}).get(name)
    if custom and os.path.exists(custom):
        return custom
    key = classe.lower().replace(" ", "_") if classe else ""
    path = CLASSE_TO_SKIN.get(key, "skin/character.png")
    return path if os.path.exists(path) else "skin/character.png"


class OverlayBar:
    def __init__(self, parent_root, app):
        self.app = app
        self.win = tk.Toplevel(parent_root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=BG_COLOR)
        self.win.withdraw()

        self._drag_x = 0
        self._drag_y = 0
        self._accounts = []
        self._active_name = None
        self._image_cache = {}
        self._btns = {}       # name -> canvas item ids dict
        self._canvas = None
        self._visible = False

        self.win.bind("<Button-1>", self._on_drag_start)
        self.win.bind("<B1-Motion>", self._on_drag_move)

    # ── Visibility ──────────────────────────────────────────────────────────

    def show(self):
        if not self._accounts:
            return
        self._visible = True
        self._position()
        self.win.deiconify()
        self.win.lift()

    def hide(self):
        self._visible = False
        self.win.withdraw()

    def is_visible(self):
        return self._visible

    # ── Rebuild (called after refresh) ──────────────────────────────────────

    def rebuild(self, accounts):
        self._accounts = [a for a in accounts if a.get("active", True)]
        self._image_cache.clear()
        self._btns.clear()
        if self._canvas:
            self._canvas.destroy()
        self._build_canvas()
        if self._visible:
            self._position()
            self.win.deiconify()
            self.win.lift()

    def _build_canvas(self):
        n = len(self._accounts)
        bar_width = max(BTN_SIZE * n + 40, 80)  # +40 for the expand button

        canvas = tk.Canvas(
            self.win,
            width=bar_width,
            height=BAR_HEIGHT,
            bg=BG_COLOR,
            highlightthickness=0,
        )
        canvas.pack(fill="both", expand=True)
        self._canvas = canvas
        self.win.geometry(f"{bar_width}x{BAR_HEIGHT}")

        # Draw rounded-ish background
        canvas.create_rectangle(0, 0, bar_width, BAR_HEIGHT, fill=BG_COLOR, outline="#2c3e50", width=1)

        for i, acc in enumerate(self._accounts):
            x = i * BTN_SIZE
            self._draw_account_btn(canvas, acc, x, i)

        # Expand / restore UI button on the right
        ex = n * BTN_SIZE
        expand_id = canvas.create_text(
            ex + 20, BAR_HEIGHT // 2,
            text="⊞",
            fill=TEXT_COLOR,
            font=("Segoe UI", 14),
        )
        canvas.tag_bind(expand_id, "<Button-1>", lambda e: self._on_expand())
        canvas.tag_bind(expand_id, "<Enter>", lambda e: canvas.itemconfig(expand_id, fill=ACTIVE_COLOR))
        canvas.tag_bind(expand_id, "<Leave>", lambda e: canvas.itemconfig(expand_id, fill=TEXT_COLOR))

        # Drag bindings on canvas background
        canvas.bind("<Button-1>", self._on_drag_start)
        canvas.bind("<B1-Motion>", self._on_drag_move)

    def _draw_account_btn(self, canvas, acc, x, idx):
        name = acc["name"]
        classe = acc.get("classe", "Inconnu")
        label = self.app.config.data.get("account_labels", {}).get(name, "")
        display = (label if label else name)[:9]

        is_active = (name == self._active_name)
        border_color = ACTIVE_COLOR if is_active else INACTIVE_COLOR

        # Background rect for this button
        bg_id = canvas.create_rectangle(
            x + 2, 2, x + BTN_SIZE - 2, BAR_HEIGHT - 2,
            fill=INACTIVE_COLOR if not is_active else "#1a3a2a",
            outline=border_color,
            width=2,
            tags=(f"btn_{name}",),
        )

        # Icon
        icon_path = get_account_icon_path(name, classe, self.app.config)
        photo = self._load_icon(icon_path)
        icon_y = 10
        if photo:
            icon_id = canvas.create_image(x + BTN_SIZE // 2, icon_y + ICON_SIZE // 2, image=photo, tags=(f"btn_{name}",))
        else:
            icon_id = None

        # Name label
        text_id = canvas.create_text(
            x + BTN_SIZE // 2, icon_y + ICON_SIZE + 4,
            text=display,
            fill=ACTIVE_COLOR if is_active else TEXT_COLOR,
            font=("Segoe UI", 8, "bold" if is_active else "normal"),
            tags=(f"btn_{name}",),
        )

        self._btns[name] = {"bg": bg_id, "text": text_id, "x": x}

        # Hover + click bindings
        for tag_item in [bg_id, text_id] + ([icon_id] if icon_id else []):
            canvas.tag_bind(tag_item, "<Enter>",
                lambda e, n=name: self._on_btn_hover(n, True))
            canvas.tag_bind(tag_item, "<Leave>",
                lambda e, n=name: self._on_btn_hover(n, False))
            canvas.tag_bind(tag_item, "<Button-1>",
                lambda e, a=acc: self._on_btn_click(a))

    def _load_icon(self, path):
        if path in self._image_cache:
            return self._image_cache[path]
        try:
            img = Image.open(path).convert("RGBA").resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._image_cache[path] = photo
            return photo
        except Exception:
            self._image_cache[path] = None
            return None

    # ── Active account highlight ─────────────────────────────────────────────

    def set_active(self, name):
        if self._active_name == name:
            return
        self._active_name = name
        if not self._canvas:
            return
        for acc_name, ids in self._btns.items():
            is_active = (acc_name == name)
            self._canvas.itemconfig(
                ids["bg"],
                fill="#1a3a2a" if is_active else INACTIVE_COLOR,
                outline=ACTIVE_COLOR if is_active else INACTIVE_COLOR,
            )
            self._canvas.itemconfig(
                ids["text"],
                fill=ACTIVE_COLOR if is_active else TEXT_COLOR,
                font=("Segoe UI", 8, "bold" if is_active else "normal"),
            )

    # ── Interactions ─────────────────────────────────────────────────────────

    def _on_btn_hover(self, name, entering):
        if not self._canvas or name not in self._btns:
            return
        ids = self._btns[name]
        is_active = (name == self._active_name)
        if entering:
            self._canvas.itemconfig(ids["bg"], fill=HOVER_COLOR if not is_active else "#22502e")
        else:
            self._canvas.itemconfig(ids["bg"], fill="#1a3a2a" if is_active else INACTIVE_COLOR)

    def _on_btn_click(self, acc):
        self.app.logic.focus_window(acc["hwnd"])
        # Update current_idx in app
        cycle = self.app.logic.get_cycle_list()
        for i, a in enumerate(cycle):
            if a["name"] == acc["name"]:
                self.app.current_idx = i
                break
        self.set_active(acc["name"])

    def _on_expand(self):
        self.hide()
        self.app.gui.root.after(0, lambda: (
            self.app.gui.root.deiconify(),
            self.app.gui.root.lift(),
            self.app.gui.root.focus_force(),
        ))

    # ── Drag ────────────────────────────────────────────────────────────────

    def _on_drag_start(self, event):
        self._drag_x = event.x_root - self.win.winfo_x()
        self._drag_y = event.y_root - self.win.winfo_y()

    def _on_drag_move(self, event):
        new_x = event.x_root - self._drag_x
        new_y = event.y_root - self._drag_y
        self.win.geometry(f"+{new_x}+{new_y}")
        self.app.config.data["overlay_x"] = new_x
        self.app.config.data["overlay_y"] = new_y
        self.app.config.save()

    # ── Positioning ──────────────────────────────────────────────────────────

    def _position(self):
        saved_x = self.app.config.data.get("overlay_x")
        saved_y = self.app.config.data.get("overlay_y")
        if saved_x is not None and saved_y is not None:
            self.win.geometry(f"+{saved_x}+{saved_y}")
        else:
            # Default: bottom-center of screen
            sw = self.win.winfo_screenwidth()
            n = max(len(self._accounts), 1)
            bar_w = BTN_SIZE * n + 40
            x = (sw - bar_w) // 2
            y = self.win.winfo_screenheight() - BAR_HEIGHT - 60
            self.win.geometry(f"+{x}+{y}")
