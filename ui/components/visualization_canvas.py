import tkinter as tk
from tkinter import ttk
from ui.components.tooltip import Tooltip

class VisualizationCanvas(tk.Canvas):
    def __init__(self, parent, on_click_command, height=35):
        super().__init__(parent, height=height, bg="#ecf0f1")
        self.bind("<Button-1>", self.on_click)
        self.bind("<Motion>", self.on_hover)
        self.on_click_command = on_click_command
        self.viz_segments = []
        self.tooltips = {} # tag_id -> tooltip object

    def draw_segments(self, segments, total_capacity_mb):
        self.delete("all")
        self.viz_segments = segments
        self.tooltips = {} # Clear tooltips

        if total_capacity_mb <= 0: return
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10: w = 900

        current_x = 0
        total_seg_size = sum(s['size'] for s in segments)
        render_max = max(total_capacity_mb, total_seg_size)
        scale = w / render_max if render_max > 0 else 1

        for i, seg in enumerate(segments):
            width = seg["size"] * scale
            outline = seg.get("outline", "white")
            tag_id = f"seg_{i}"

            # Use distinct stipple for future data partition
            stipple = "gray50" if seg.get('is_future_data') else ""

            rect_id = self.create_rectangle(
                current_x, 0, current_x + width, h,
                fill=seg["color"], outline=outline, width=1,
                tags=(tag_id, "segment"), stipple=stipple
            )

            if width > 40:
                name_short = seg['name'][:15]
                text_color = "black" if seg["color"] in ["white", "#ecf0f1", "#bdc3c7", "#50e3c2"] else "white"
                self.create_text(
                    current_x + width/2, h/2,
                    text=name_short, fill=text_color, font=("Arial", 9, "bold"),
                    tags=(tag_id, "segment")
                )

            current_x += width

    def on_click(self, event):
        if self.on_click_command:
            self.on_click_command(event)

    def on_hover(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        item = self.find_closest(x, y)
        tags = self.gettags(item)

        # Simple tooltip logic: Create a temp label or use existing Tooltip class if adapted
        # Since standard Tooltip class is widget-based, we might need a canvas-specific one.
        # For now, let's just print to console for verification or use a simple floating label if feasible.
        # Actually, let's use the provided `ui.components.tooltip` but we need to bind it to the *canvas* and update text.

        for tag in tags:
            if tag.startswith("seg_"):
                idx = int(tag.split("_")[1])
                if 0 <= idx < len(self.viz_segments):
                    seg = self.viz_segments[idx]
                    text = f"{seg['name']}\nSize: {seg['size']:.1f} MB"
                    # We can't easily use the widget tooltip class for specific items.
                    # Implementing a simple canvas tooltip here.
                    self.show_canvas_tooltip(event.x_root, event.y_root, text)
                return

        self.hide_canvas_tooltip()

    def show_canvas_tooltip(self, x, y, text):
        if hasattr(self, '_tooltip_win') and self._tooltip_win:
            self._tooltip_label.config(text=text)
            self._tooltip_win.geometry(f"+{x+15}+{y+15}")
            return

        self._tooltip_win = tk.Toplevel(self)
        self._tooltip_win.wm_overrideredirect(True)
        self._tooltip_win.geometry(f"+{x+15}+{y+15}")
        self._tooltip_label = tk.Label(self._tooltip_win, text=text, background="#ffffe0", relief="solid", borderwidth=1)
        self._tooltip_label.pack()

    def hide_canvas_tooltip(self):
        if hasattr(self, '_tooltip_win') and self._tooltip_win:
            self._tooltip_win.destroy()
            self._tooltip_win = None
