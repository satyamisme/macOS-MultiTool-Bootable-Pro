"""
gui_tkinter.py - Tkinter-based GUI for macOS Multi-Tool Pro
ONE RESPONSIBILITY: Provide a graphical interface for the tool
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys
import os
import queue

# Import core modules (adapt as needed for GUI context)
from detection import installer_scanner, disk_detector
from core import privilege

class MultiBootGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("macOS Multi-Tool Pro")
        self.root.geometry("600x500")

        # Variables
        self.selected_disk = tk.StringVar()
        self.installers_list = []
        self.selected_installers = []

        # Layout
        self.create_widgets()

        # Initial scan
        self.refresh_hardware()

    def create_widgets(self):
        # Header
        header = ttk.Label(self.root, text="macOS Multi-Boot Creator", font=("Arial", 16, "bold"))
        header.pack(pady=10)

        # Disk Selection
        disk_frame = ttk.LabelFrame(self.root, text="Select Target USB Drive")
        disk_frame.pack(fill="x", padx=10, pady=5)

        self.disk_combo = ttk.Combobox(disk_frame, textvariable=self.selected_disk, state="readonly")
        self.disk_combo.pack(fill="x", padx=5, pady=5)

        refresh_btn = ttk.Button(disk_frame, text="Refresh Drives", command=self.refresh_hardware)
        refresh_btn.pack(anchor="e", padx=5, pady=2)

        # Installer Selection
        inst_frame = ttk.LabelFrame(self.root, text="Select Installers")
        inst_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.inst_tree = ttk.Treeview(inst_frame, columns=("Version", "Size"), show="headings", selectmode="extended")
        self.inst_tree.heading("Version", text="Version")
        self.inst_tree.heading("Size", text="Size")
        self.inst_tree.pack(fill="both", expand=True, padx=5, pady=5)

        scan_btn = ttk.Button(inst_frame, text="Rescan Installers", command=self.scan_installers)
        scan_btn.pack(anchor="e", padx=5, pady=2)

        # Actions
        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill="x", padx=10, pady=10)

        self.create_btn = ttk.Button(action_frame, text="Create Bootable USB", command=self.start_creation)
        self.create_btn.pack(side="right")

        # Log Output
        log_frame = ttk.LabelFrame(self.root, text="Log Output")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def refresh_hardware(self):
        self.log("Scanning for USB drives...")
        drives = disk_detector.get_external_usb_drives()
        options = []
        if drives:
            for d in drives:
                options.append(f"{d['name']} ({d['id']}) - {d['size_gb']:.1f} GB")
            self.disk_combo['values'] = options
            self.disk_combo.current(0)
            self.log(f"Found {len(drives)} drive(s).")
        else:
            self.disk_combo['values'] = ["No external USB drives found"]
            self.disk_combo.current(0)
            self.log("No drives found.")

        self.scan_installers()

    def scan_installers(self):
        self.log("Scanning for macOS installers...")
        # Clear tree
        for item in self.inst_tree.get_children():
            self.inst_tree.delete(item)

        self.installers_list = installer_scanner.scan_for_installers()

        if self.installers_list:
            for inst in self.installers_list:
                size_gb = inst['size_kb'] / (1024 * 1024)
                self.inst_tree.insert("", "end", values=(inst['name'], f"{inst['version']}", f"{size_gb:.2f} GB"))
            self.log(f"Found {len(self.installers_list)} installer(s).")
        else:
            self.log("No installers found.")

    def start_creation(self):
        # Placeholder for actual logic integration
        # Real implementation would call operations.partitioner, installer_runner, etc.
        # running in a separate thread to keep UI responsive.
        selected_indices = self.inst_tree.selection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one installer.")
            return

        disk_str = self.selected_disk.get()
        if "No external" in disk_str or not disk_str:
            messagebox.showwarning("Warning", "Please select a target disk.")
            return

        if messagebox.askyesno("Confirm", "This will ERASE the target drive. Continue?"):
            self.log("Starting creation process (Simulation)...")
            # Threading logic here...

def launch():
    if os.geteuid() != 0:
        messagebox.showerror("Error", "Root privileges required. Run with sudo.")
        return

    root = tk.Tk()
    app = MultiBootGUI(root)
    root.mainloop()

if __name__ == "__main__":
    launch()
