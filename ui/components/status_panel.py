import tkinter as tk
from tkinter import ttk

class StatusPanel(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Progress & Status")
        self.create_widgets()

    def create_widgets(self):
        # Notebook for Log vs Progress
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 1: Visual Progress
        self.progress_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.progress_frame, text="Progress")

        # Main Progress Bar
        self.main_progress = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.main_progress.pack(fill="x", padx=10, pady=10)

        self.status_label = ttk.Label(self.progress_frame, text="Ready", font=("Arial", 10))
        self.status_label.pack(pady=5)

        # Phase List
        self.phase_labels = {}
        phases = ["Downloading", "Partitioning", "Installing", "Finalizing"]
        for p in phases:
            lbl = ttk.Label(self.progress_frame, text=f"• {p}", foreground="gray")
            lbl.pack(anchor="w", padx=20)
            self.phase_labels[p] = lbl

        # Tab 2: Log
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="Details Log")

        import tkinter.scrolledtext as st
        self.log_text = st.ScrolledText(self.log_frame, height=8, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", str(message) + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        # Also update status label if short
        if len(str(message)) < 50:
            self.status_label.config(text=str(message))

    def set_phase(self, phase_name):
        for name, lbl in self.phase_labels.items():
            if name == phase_name:
                lbl.config(foreground="blue", font=("Arial", 10, "bold"))
            else:
                lbl.config(foreground="gray", font=("Arial", 9))
