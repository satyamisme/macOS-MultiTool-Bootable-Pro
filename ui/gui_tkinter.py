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
    def __init__(self, root, config=None):
        self.root = root
        self.config = config
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
        selected_indices = self.inst_tree.selection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one installer.")
            return

        disk_str = self.selected_disk.get()
        if "No external" in disk_str or not disk_str:
            messagebox.showwarning("Warning", "Please select a target disk.")
            return

        # Parse disk ID from string "Name (disk2) - Size"
        disk_id = disk_str.split('(')[1].split(')')[0]

        if messagebox.askyesno("Confirm", f"This will ERASE {disk_id}. Continue?"):
            self.log("Starting creation process...")
            self.create_btn.config(state="disabled")

            # Identify selected installers
            # Indices in tree might not match list if sorted, but we populated sequentially
            # Better to find by ID/Values
            selected_items = [self.inst_tree.item(i)['values'] for i in selected_indices]
            # Match back to self.installers_list
            target_installers = []
            for item in selected_items:
                name = item[0]
                version = item[1]
                for inst in self.installers_list:
                    if inst['name'] == name and str(inst['version']) == str(version):
                        target_installers.append(inst)
                        break

            # Start thread
            threading.Thread(target=self.run_creation_thread, args=(disk_id, target_installers)).start()

    def run_creation_thread(self, disk_id, installers):
        # We need to capture output. Redirecting stdout is tricky with threads safely.
        # Ideally, main logic should accept a logger callback.
        # For now, we simulate progress or call the logic directly and hope it prints to stdout
        # which we can't easily capture in Tkinter text box without redirecting sys.stdout.

        self.log("Preparing partitions...")
        # Call operations.partitioner.create_multiboot_layout...
        # Since we are in a GUI, we should probably wrap this better.
        # For prototype, we log completion.

        import time
        time.sleep(1) # Simulation
        self.log(f"Partitioning {disk_id}...")

        # Real logic would be:
        # success = partitioner.create_multiboot_layout(disk_id, installers, ...)

        self.log("Installing macOS versions...")
        for inst in installers:
            self.log(f"Installing {inst['name']}...")
            time.sleep(2) # Simulation

        self.log("Done! (Prototype Mode)")
        self.root.after(0, lambda: self.create_btn.config(state="normal"))

def launch(config=None):
    if os.geteuid() != 0:
        # Tkinter might fail to initialize if sudo environment is weird, but usually fine.
        # Just warn.
        # messagebox is part of Tk, need root first.
        pass

    root = tk.Tk()
    app = MultiBootGUI(root, config)
    root.mainloop()

if __name__ == "__main__":
    launch()
