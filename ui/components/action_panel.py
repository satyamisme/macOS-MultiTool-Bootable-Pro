import tkinter as tk
from tkinter import ttk

class ActionPanel(ttk.Frame):
    def __init__(self, parent, on_create_click):
        super().__init__(parent)
        self.on_create_click = on_create_click
        self.create_widgets()

    def create_widgets(self):
        # Pending Changes Bar (Optional enhancement)
        self.pending_label = ttk.Label(self, text="", foreground="gray")
        self.pending_label.pack(fill="x", pady=(0, 5))

        self.create_btn = ttk.Button(self, text="CREATE BOOTABLE USB", command=self.on_create_click)
        self.create_btn.pack(fill="x", padx=20, pady=10)

    def set_button_text(self, text, state="normal"):
        self.create_btn.config(text=text, state=state)
