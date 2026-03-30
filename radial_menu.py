import tkinter as tk
import math
import win32api
import os
from PIL import Image, ImageTk
from utils import resource_path

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame


class RadialMenu:
    def __init__(self, parent_root, on_select_callback, accent_color="#3498db", hover_color="#2980b9", center_icon_path=None):
        self.window = tk.Toplevel(parent_root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-transparentcolor", "magenta")
        
        self.size = 400 
        self.center = self.size / 2
        self.radius_outer = 175 
        self.radius_inner = 35
        
        self.accent_color = accent_color
        self.hover_color = hover_color
        
        self.canvas = tk.Canvas(self.window, width=self.size, height=self.size, bg="magenta", highlightthickness=0)
        self.canvas.pack()
        
        self.on_select_callback = on_select_callback
        self.items = [] 
        self.arcs = []
        self.hovered_index = -1
        self.is_open = False
        self.image_cache = {} 
        self.base_volume = 0.5 
        self.current_name = None
        
        try:
            pygame.mixer.init()
            self.mixer_active = True
            
            hover_path = resource_path("sounds", "hover.wav")  # ← corrigido
            click_path = resource_path("sounds", "click.wav")  # ← corrigido
            
            self.sound_hover = pygame.mixer.Sound(hover_path) if os.path.exists(hover_path) else None
            self.sound_click = pygame.mixer.Sound(click_path) if os.path.exists(click_path) else None
            
            self.set_base_volume(0.5) 
            
        except Exception as e:
            print(f"Erreur d'initialisation du son : {e}")
            self.mixer_active = False

        self.center_image = None
        if center_icon_path and os.path.exists(center_icon_path):
            try:
                img = Image.open(center_icon_path).resize((40, 40), Image.Resampling.LANCZOS)
                self.center_image = ImageTk.PhotoImage(img)
            except Exception:
                pass
        
        self.window.withdraw()

    def set_base_volume(self, volume):
        self.base_volume = volume
        if self.mixer_active:
            if self.sound_hover: self.sound_hover.set_volume(0.3 * self.base_volume)
            if self.sound_click: self.sound_click.set_volume(0.8 * self.base_volume)

    def load_image(self, class_name):
        filename = f"{class_name}_retro" if getattr(self, 'is_retro', False) and class_name != "Inconnu" else class_name
        
        if filename in self.image_cache: return self.image_cache[filename]
        path = resource_path("skin", f"{filename}.png")  # ← corrigido
        if not os.path.exists(path): return None
        try:
            img = Image.open(path).resize((36, 36), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.image_cache[filename] = photo
            return photo
        except Exception:
            return None

    def show(self, x, y, items, current_name=None, is_retro=False):
        if not items: return
        self.items = items
        self.current_name = current_name
        self.is_retro = is_retro
        
        self.build_wheel()
        pos_x = int(x - self.center)
        pos_y = int(y - self.center)
        self.window.geometry(f"+{pos_x}+{pos_y}")
        self.window.deiconify()
        self.is_open = True
        self.hovered_index = -1 
        self.update_hover()

    def hide(self):
        if not self.is_open: return
        self.is_open = False
        self.window.withdraw()
        
        if self.hovered_index != -1 and self.hovered_index < len(self.items):
            if self.mixer_active and self.sound_click:
                self.sound_click.play()
            selected_name = self.items[self.hovered_index]['name']
            self.on_select_callback(selected_name)

    def build_wheel(self):
        self.canvas.delete("all")
        self.arcs.clear()
        nb_items = len(self.items)
        angle_per_item = 360 / nb_items
        bbox = (self.center - self.radius_outer, self.center - self.radius_outer, self.center + self.radius_outer, self.center + self.radius_outer)
        
        for i, item in enumerate(self.items):
            start = 90 - (i + 1) * angle_per_item
            is_active = (item['name'] == self.current_name)
            base_color = "#1c456d" if is_active else "#2b2b2b"
            
            arc = self.canvas.create_arc(bbox, start=start, extent=angle_per_item, fill=base_color, outline="#3d3d3d", width=2) 
            self.arcs.append(arc)
            
            mid_angle = math.radians(start + (angle_per_item / 2))
            base_x = self.center + math.cos(mid_angle) * (self.radius_outer * 0.65)
            base_y = self.center - math.sin(mid_angle) * (self.radius_outer * 0.65)
            img_y = base_y - 12
            txt_y = base_y + 18
            
            skin_img = self.load_image(item['classe'])
            if skin_img: self.canvas.create_image(base_x, img_y, image=skin_img)
            display_text = item['name'][:10] 
            self.canvas.create_text(base_x, txt_y, text=display_text, fill="#ecf0f1", font=("Segoe UI", 9, "bold"))
            
        self.canvas.create_oval(self.center - self.radius_inner, self.center - self.radius_inner, self.center + self.radius_inner, self.center + self.radius_inner, fill="#1a1a1a", outline="#3d3d3d", width=2)
        if self.center_image: self.canvas.create_image(self.center, self.center, image=self.center_image)
        else: self.canvas.create_oval(self.center - 4, self.center - 4, self.center + 4, self.center + 4, fill=self.accent_color, outline="")

    def update_hover(self):
        if not self.is_open: return
        x_mouse, y_mouse = win32api.GetCursorPos()
        x_center = self.window.winfo_rootx() + self.center
        y_center = self.window.winfo_rooty() + self.center
        distance = math.hypot(x_mouse - x_center, y_mouse - y_center)
        
        if distance < self.radius_inner or distance > self.radius_outer:
            self.highlight_slice(-1)
        else:
            dx = x_mouse - x_center
            dy = y_mouse - y_center
            cw_angle = (math.degrees(math.atan2(dx, -dy)) + 360) % 360
            angle_per_item = 360 / len(self.items)
            index = int(cw_angle // angle_per_item)
            self.highlight_slice(index)
            
        self.window.after(15, self.update_hover)

    def highlight_slice(self, index):
        if index == self.hovered_index: return 
        self.hovered_index = index
        if index != -1 and self.mixer_active and self.sound_hover:
            self.sound_hover.play()
            
        for i, arc in enumerate(self.arcs):
            is_active = (getattr(self, 'current_name', None) == self.items[i]['name'])
            base_color = "#1c456d" if is_active else "#2b2b2b"
            color = self.hover_color if i == index else base_color
            outline_color = self.accent_color if i == index else "#3d3d3d"
            self.canvas.itemconfig(arc, fill=color, outline=outline_color)