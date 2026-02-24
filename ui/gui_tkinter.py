"""
gui_tkinter.py - Tkinter-based GUI for macOS Multi-Tool Pro
ONE RESPONSIBILITY: Provide a graphical interface for the tool
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import threading
import sys
import os
import queue
import subprocess
import time
import json
import math

# Import core modules
from detection import installer_scanner, disk_detector
from core import privilege, constants, config_manager
from operations import partitioner, installer_runner, branding, updater
from integration import mist_downloader

class MultiBootGUI:
    def __init__(self, root, config=None):
        self.root = root
        self.config = config_manager.load_config()
        self.root.title("macOS Multi-Tool Pro")

        # Restore window geometry
        w = self.config.get("window_width", 1000)
        h = self.config.get("window_height", 850)
        self.root.geometry(f"{w}x{h}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Variables
        self.selected_disk = tk.StringVar()
        self.installers_list = []
        self.log_queue = queue.Queue()
        self.is_working = False

        # State
        self.current_disk_size_gb = 0.0
        self.total_required_gb = 0.0
        self.custom_buffers = {}
        self.existing_installers_map = {} # Store existing content
        self.drive_structure = None # Detailed structure

        # UI State
        self.show_all_disks_var = tk.BooleanVar(value=False)

        # Restore last mode
        last_mode = self.config.get("last_mode", "create")
        self.mode_var = tk.StringVar(value=last_mode)

        # Layout
        self.create_widgets()

        # Trigger mode update visually
        self.root.after(100, self.on_mode_change)

        # Bind Shortcuts
        self.root.bind("<Command-n>", lambda e: self.set_mode("create"))
        self.root.bind("<Control-n>", lambda e: self.set_mode("create"))
        self.root.bind("<Command-u>", lambda e: self.set_mode("update"))
        self.root.bind("<Control-u>", lambda e: self.set_mode("update"))
        self.root.bind("<Command-o>", lambda e: self.optimize_buffers())
        self.root.bind("<Control-o>", lambda e: self.optimize_buffers())

        # Start log poller
        self.poll_log_queue()

        # Initial scan
        self.refresh_hardware()

    def set_mode(self, mode):
        self.mode_var.set(mode)
        self.on_mode_change()

    def on_close(self):
        # Save config
        self.config["last_mode"] = self.mode_var.get()
        self.config["window_width"] = self.root.winfo_width()
        self.config["window_height"] = self.root.winfo_height()
        self.config["default_buffer"] = self.buffer_var.get()
        config_manager.save_config(self.config)
        self.root.destroy()

    def create_widgets(self):
        # Menu Bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Refresh All", command=self.refresh_hardware)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Format Disk (Erase All)", command=self.format_disk_dialog)
        tools_menu.add_command(label="Download macOS Installers...", command=self.open_download_dialog)

        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(header_frame, text="macOS Multi-Boot Creator", font=("Arial", 18, "bold")).pack(side="left")
        ttk.Button(header_frame, text="Refresh", command=self.refresh_hardware).pack(side="right")

        # Main PanedWindow
        paned = ttk.PanedWindow(self.root, orient="vertical")
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        # Top Section: Selection
        top_frame = ttk.Frame(paned)
        paned.add(top_frame, weight=1)

        # Left: Disk Selection
        disk_frame = ttk.LabelFrame(top_frame, text="1. Select Target USB Drive")
        disk_frame.pack(fill="x", padx=5, pady=5)

        self.disk_combo = ttk.Combobox(disk_frame, textvariable=self.selected_disk, state="readonly", width=60)
        self.disk_combo.pack(fill="x", padx=10, pady=10)
        self.disk_combo.bind("<<ComboboxSelected>>", self.on_disk_selected)

        # Options Frame (Mode Switch)
        opt_frame = ttk.Frame(disk_frame)
        opt_frame.pack(fill="x", padx=10, pady=5)

        ttk.Checkbutton(opt_frame, text="Show All Disks (Advanced)",
                        variable=self.show_all_disks_var,
                        command=self.refresh_hardware).pack(side="left")

        # Mode Selection Radiobuttons
        ttk.Label(opt_frame, text="Mode:").pack(side="left", padx=(20, 5))
        ttk.Radiobutton(opt_frame, text="Create New (Erase)", variable=self.mode_var, value="create", command=self.on_mode_change).pack(side="left", padx=5)
        ttk.Radiobutton(opt_frame, text="Update Existing", variable=self.mode_var, value="update", command=self.on_mode_change).pack(side="left", padx=5)

        # Existing Content Panel (Visible in Update Mode)
        self.content_frame = ttk.LabelFrame(top_frame, text="Existing Drive Content")
        # Initially hidden, packed in on_mode_change if update

        cols = ("Partition", "Size", "Latest Version", "Action")
        self.content_tree = ttk.Treeview(self.content_frame, columns=cols, show="headings", height=5)
        for col in cols:
            self.content_tree.heading(col, text=col)
            self.content_tree.column(col, width=100)
        self.content_tree.column("Partition", width=200)
        self.content_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Content Actions
        cbtn_frame = ttk.Frame(self.content_frame)
        cbtn_frame.pack(side="right", fill="y", padx=5, pady=5)
        ttk.Button(cbtn_frame, text="Delete Partition", command=self.delete_existing_partition).pack(fill="x", pady=2)
        ttk.Button(cbtn_frame, text="Check Updates", command=self.check_for_updates).pack(fill="x", pady=2)
        ttk.Button(cbtn_frame, text="Scan Content", command=lambda: self.on_disk_selected(None)).pack(fill="x", pady=2)

        # Middle: Installer Selection
        inst_frame = ttk.LabelFrame(top_frame, text="2. Select macOS Installers (To Add/Update)")
        inst_frame.pack(fill="both", expand=True, padx=5, pady=5)

        cols = ("Select", "Name", "Version", "Size", "Buffer", "Status")
        self.inst_tree = ttk.Treeview(inst_frame, columns=cols, show="headings", selectmode="extended", height=10)

        self.inst_tree.heading("Select", text="[x]")
        self.inst_tree.column("Select", width=40, anchor="center")
        self.inst_tree.heading("Name", text="Name")
        self.inst_tree.column("Name", width=250)
        self.inst_tree.heading("Version", text="Version")
        self.inst_tree.column("Version", width=80)
        self.inst_tree.heading("Size", text="Size")
        self.inst_tree.column("Size", width=80)
        self.inst_tree.heading("Buffer", text="Buffer")
        self.inst_tree.column("Buffer", width=60)
        self.inst_tree.heading("Status", text="Status")
        self.inst_tree.column("Status", width=80)

        self.inst_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.inst_tree.bind("<Button-1>", self.on_tree_click)
        self.inst_tree.bind("<Double-1>", self.on_tree_double_click)

        scrollbar = ttk.Scrollbar(inst_frame, orient="vertical", command=self.inst_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.inst_tree.configure(yscrollcommand=scrollbar.set)

        self.context_menu = tk.Menu(self.inst_tree, tearoff=0)
        self.context_menu.add_command(label="Edit Buffer Size", command=self.edit_selected_buffer)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete Installer", command=self.delete_selected_installer)
        self.inst_tree.bind("<Button-3>", self.show_context_menu)

        btn_frame = ttk.Frame(inst_frame)
        btn_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        ttk.Button(btn_frame, text="Select All", command=self.select_all_installers).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Unselect All", command=self.deselect_all_installers).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_selected_installer).pack(side="left", padx=20)
        ttk.Button(btn_frame, text="Download New...", command=self.open_download_dialog).pack(side="right", padx=2)

        # Bottom Section
        bottom_frame = ttk.Frame(paned)
        paned.add(bottom_frame, weight=1)

        settings_frame = ttk.LabelFrame(bottom_frame, text="3. Settings & Space Check")
        settings_frame.pack(fill="x", padx=5, pady=5)

        buffer_frame = ttk.Frame(settings_frame)
        buffer_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(buffer_frame, text="Default Safety Buffer (GB):").pack(side="left", padx=5)

        # Restore default buffer
        def_buf = self.config.get("default_buffer", 2.0)
        self.buffer_var = tk.DoubleVar(value=def_buf)

        self.buffer_scale = ttk.Scale(buffer_frame, from_=0.1, to=10.0, variable=self.buffer_var, orient="horizontal")
        self.buffer_scale.pack(side="left", fill="x", expand=True, padx=5)
        self.buffer_label = ttk.Label(buffer_frame, text=f"{def_buf:.1f} GB")
        self.buffer_label.pack(side="left", padx=5)
        self.buffer_scale.configure(command=self.on_buffer_change)

        ttk.Button(buffer_frame, text="Optimize Density (Smart)", command=self.optimize_buffers).pack(side="right", padx=10)

        self.space_label = ttk.Label(settings_frame, text="Required: 0.0 GB | Available: 0.0 GB | Select Installers & Disk", font=("Arial", 10, "bold"))
        self.space_label.pack(fill="x", padx=10, pady=10)

        self.viz_canvas = tk.Canvas(settings_frame, height=35, bg="#ecf0f1")
        self.viz_canvas.pack(fill="x", padx=10, pady=5)
        self.viz_canvas.bind("<Button-1>", self.on_viz_click)

        self.create_btn = ttk.Button(bottom_frame, text="CREATE BOOTABLE USB", command=self.start_creation)
        self.create_btn.pack(fill="x", padx=20, pady=10)

        log_frame = ttk.LabelFrame(bottom_frame, text="Progress Log")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state="disabled", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    # --- Event Handlers ---

    def check_for_updates(self):
        """Check Mist for latest versions of installed OSes."""
        if not self.drive_structure: return

        self.log("Checking for updates via Mist...")
        threading.Thread(target=self.run_check_updates).start()

    def run_check_updates(self):
        try:
            if not mist_downloader.check_mist_available():
                self.log("Mist-CLI not available.")
                return

            existing = self.drive_structure.get('existing_partitions', [])
            updates_found = 0

            for part in existing:
                name = part['clean_name'] # e.g. "High Sierra"
                # Search Mist for this name
                # mist list installer "High Sierra" --output-type json
                # This returns list. We want the latest.

                # Check cache or fetch
                installers = mist_downloader.list_installers(name)
                if installers:
                    # Find latest compatible? Or just latest.
                    # list_installers already marks 'latest'.
                    latest_ver = "Unknown"
                    for inst in installers:
                         if inst.get('latest'):
                             latest_ver = f"{inst['version']} ({inst['build']})"
                             break

                    # Update Treeview
                    # Find item by tag
                    for item in self.content_tree.get_children():
                         item_tags = self.content_tree.item(item, "tags")
                         if part['id'] in item_tags:
                             # Update value
                             curr_vals = self.content_tree.item(item)['values']
                             # (Name, Size, Latest, Action)
                             self.content_tree.item(item, values=(curr_vals[0], curr_vals[1], latest_ver, curr_vals[3]))
                             updates_found += 1

            self.log(f"Update check complete. Checked {updates_found} partitions.")

        except Exception as e:
            self.log(f"Update check failed: {e}")

    def optimize_buffers(self):
        if not messagebox.askyesno("Optimize Density", "Apply version-aware minimum buffers?\n\nThis will reduce overhead to fit more installers, but leaves less room for OS updates/caching.\n\n• macOS 14+: 0.8 GB\n• macOS 12-13: 0.5 GB\n• Older: 0.3 GB"):
            return

        updates_made = 0
        for item in self.inst_tree.get_children():
            values = self.inst_tree.item(item)['values']
            name = values[1]
            ver = str(values[2])

            # Smart Logic
            try:
                major = int(ver.split('.')[0])
            except:
                major = 10

            smart_buffer = 0.5 # Default
            if major >= 14: smart_buffer = 0.8
            elif major >= 12: smart_buffer = 0.5
            else: smart_buffer = 0.3

            key = f"{name}_{ver}"
            self.custom_buffers[key] = smart_buffer
            self.inst_tree.set(item, "Buffer", f"{smart_buffer:.1f} GB")
            updates_made += 1

        self.update_space_usage()
        self.log(f"Optimized buffers for {updates_made} installers.")

    def on_mode_change(self):
        mode = self.mode_var.get()
        if mode == "update":
            self.create_btn.config(text="UPDATE EXISTING USB")
            self.content_frame.pack(fill="both", expand=True, padx=5, pady=5, after=self.disk_combo.master)
            self.on_disk_selected(None)
        else:
            self.create_btn.config(text="CREATE BOOTABLE USB (Erase All)")
            self.content_frame.pack_forget()
        self.update_space_usage()

    def on_tree_click(self, event):
        region = self.inst_tree.identify("region", event.x, event.y)
        if region == "cell":
            col = self.inst_tree.identify_column(event.x)
            if col == "#1":
                item_id = self.inst_tree.identify_row(event.y)
                self.toggle_selection(item_id)
                return "break"

    def on_tree_double_click(self, event):
        item_id = self.inst_tree.identify_row(event.y)
        if item_id:
            self.edit_selected_buffer(item_id)

    def toggle_selection(self, item_id):
        if not item_id: return
        current = self.inst_tree.set(item_id, "Select")
        tags = self.inst_tree.item(item_id, "tags")
        if "stub" in tags:
            messagebox.showwarning("Invalid", "Cannot select Stub installer.")
            return
        new_val = "☑" if current == "☐" else "☐"
        self.inst_tree.set(item_id, "Select", new_val)
        self.update_space_usage()

    def edit_selected_buffer(self, item_id=None):
        if not item_id:
            sel = self.inst_tree.selection()
            if sel: item_id = sel[0]
            else: return
        values = self.inst_tree.item(item_id)['values']
        name = values[1]
        current_buffer = values[4]
        new_val = simpledialog.askfloat("Buffer Size", f"Enter buffer size (GB) for {name}:",
                                        minvalue=0.1, maxvalue=20.0, initialvalue=float(current_buffer.split()[0]))
        if new_val is not None:
            key = f"{name}_{values[2]}"
            self.custom_buffers[key] = new_val
            self.inst_tree.set(item_id, "Buffer", f"{new_val:.1f} GB")
            self.update_space_usage()

    def log(self, message):
        self.log_queue.put(message)

    def poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", str(msg) + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.poll_log_queue)

    def on_buffer_change(self, value):
        val = float(value)
        self.buffer_label.configure(text=f"{val:.1f} GB")
        for item in self.inst_tree.get_children():
            values = self.inst_tree.item(item)['values']
            name_ver_key = f"{values[1]}_{values[2]}"
            if name_ver_key not in self.custom_buffers:
                self.inst_tree.set(item, "Buffer", f"{val:.1f} GB")
        self.update_space_usage()

    def on_disk_selected(self, event):
        disk_str = self.selected_disk.get()
        if not disk_str or "No external" in disk_str: return
        try:
            disk_id = disk_str.split('(')[1].split(')')[0]
            threading.Thread(target=self.scan_drive_content, args=(disk_id,)).start()
        except: pass
        self.update_space_usage()

    def scan_drive_content(self, disk_id):
        structure = updater.get_drive_structure(disk_id)
        if structure:
            self.existing_installers_map = structure.get('existing_installers', {})
            self.drive_structure = structure # Store full structure
            self.root.after(0, lambda: self.update_content_ui(structure))
            self.root.after(0, self.update_space_usage)

    def update_content_ui(self, structure):
        for item in self.content_tree.get_children():
            self.content_tree.delete(item)

        existing = structure.get('existing_partitions', [])

        for part in existing:
            size_gb = part['size'] / 1e9
            name = part['clean_name'] # e.g. "Sonoma"

            # Check if we have a matching installer in our list
            action = "Keep"
            matching_installer = None

            for inst in self.installers_list:
                # Simple name match
                if name in inst['name']:
                    matching_installer = inst
                    break

            if matching_installer:
                action = f"Reinstall ({matching_installer['version']})"

            # Placeholder for latest version check (populated by check_for_updates)
            latest = "Check Mist"

            self.content_tree.insert("", "end", values=(part['name'], f"{size_gb:.1f} GB", latest, action), tags=(part['id'],))

    def delete_existing_partition(self):
        sel = self.content_tree.selection()
        if not sel: return

        item = sel[0]
        values = self.content_tree.item(item)['values']
        part_name = values[0]
        part_id = self.content_tree.item(item, 'tags')[0]

        if messagebox.askyesno("Delete Partition", f"Delete {part_name} ({part_id})?\n\nThis frees up space immediately."):
            threading.Thread(target=self.run_delete_partition, args=(part_id,)).start()

    def run_delete_partition(self, part_id):
        self.log(f"Deleting {part_id}...")
        try:
            if updater.delete_partition(part_id):
                self.log("Deleted. Rescanning...")
                # Rescan logic
                disk_str = self.selected_disk.get()
                if disk_str:
                    disk_id = disk_str.split('(')[1].split(')')[0]
                    self.scan_drive_content(disk_id)
            else:
                self.log("Delete failed.")
        except Exception as e:
            self.log(f"Error: {e}")

    def get_selected_installers(self):
        selected = []
        for item in self.inst_tree.get_children():
            if self.inst_tree.set(item, "Select") == "☑":
                selected.append(item)
        return selected

    def update_space_usage(self, event=None):
        selected_items = self.get_selected_installers()
        is_update = self.mode_var.get() == "update"

        total_required_mb = 0.0
        if not is_update:
            total_required_mb += 1024 # EFI

        segments = []
        if not is_update:
            segments.append({"name": "EFI", "size": 1024, "color": "#bdc3c7", "type": "system"})

        # Visualize existing content if Update Mode
        existing_names = []
        # We need to map replaced partitions to avoid double counting visually
        replaced_partitions = []

        # First pass: Identify replacements to exclude them from "Existing" list drawn initially
        # Actually, we should draw existing first, but if they are replaced, we draw them as "Replacing"
        # Let's rebuild the segment list logic.

        # 1. Add Existing Partitions (if Update Mode)
        if is_update and self.drive_structure:
            for part in self.drive_structure.get('existing_partitions', []):
                size_mb = part['size'] / 1e6
                existing_names.append(part['clean_name'])
                # We will mark them as "Existing" for now, check replacement later
                segments.append({
                    "name": part['name'],
                    "size": size_mb,
                    "color": "#3498db", # Blue
                    "type": "existing",
                    "id": part['id'],
                    "clean_name": part['clean_name']
                })

        # 2. Add Selected Installers
        for item_id in selected_items:
            values = self.inst_tree.item(item_id)['values']
            name = values[1]
            version = str(values[2])
            size_kb = 0
            for inst in self.installers_list:
                if inst['name'] == name and str(inst['version']) == version:
                    size_kb = inst['size_kb']
                    break

            # Check for existing
            # If replacing, use minimal buffer (or 0 overhead assuming reuse)
            # Ideally we check drive_structure existing_partitions size vs new size

            clean_name = name.replace("Install macOS ", "").replace("Install ", "").replace(".app", "")
            is_replacing = False
            replace_target_size_mb = 0
            replaced_seg_index = -1

            # Check for existing partition to replace in our segments list
            if is_update:
                for idx, seg in enumerate(segments):
                    if seg.get('type') == 'existing':
                        # Match name
                        if clean_name in seg['clean_name'] or seg['clean_name'] in clean_name:
                            is_replacing = True
                            replace_target_size_mb = seg['size']
                            replaced_seg_index = idx
                            break

            try: buffer_gb = float(values[4].split()[0])
            except: buffer_gb = 2.0

            installer_size_mb = (size_kb / 1024)

            if is_replacing:
                # Update the existing segment to show it's being replaced
                part_size_mb = replace_target_size_mb

                color = "#e67e22" # Orange
                if installer_size_mb * 1.02 > replace_target_size_mb:
                    color = "#e74c3c" # Red (Error)

                # Update the segment in place
                segments[replaced_seg_index]['color'] = color
                segments[replaced_seg_index]['name'] = f"Replace: {name}"
                segments[replaced_seg_index]['type'] = 'replacing'
                segments[replaced_seg_index]['installer_item'] = item_id # Link to tree

            else:
                # New partition
                part_size_mb = constants.calculate_partition_size(size_kb, version, override_buffer_gb=buffer_gb)
                total_required_mb += part_size_mb

                segments.append({
                    "name": f"New: {name}",
                    "size": part_size_mb,
                    "color": "#2ecc71", # Green
                    "type": "new",
                    "installer_item": item_id
                })

        self.total_required_gb = total_required_mb / 1024.0

        # Available Space Logic
        disk_str = self.selected_disk.get()
        available_gb = 0.0

        if disk_str and "No external" not in disk_str:
            try:
                disk_id = disk_str.split('(')[1].split(')')[0]
                if is_update and self.drive_structure:
                    # In update mode, available for NEW partitions is just Free Space.
                    # Replaced partitions are handled by the 'is_replacing' logic above.
                    free_gb = self.drive_structure['free_space'] / 1e9
                    available_gb = free_gb
                else:
                    size_part = disk_str.split(' - ')[1]
                    available_gb = float(size_part.split()[0])
            except:
                available_gb = 0.0
        self.current_disk_size_gb = available_gb

        # Draw Free Space Segment
        if is_update:
             # Just append a "Free" block at end
             free_mb = available_gb * 1024
             segments.append({"name": "Free", "size": free_mb, "color": "white", "outline": "#bdc3c7", "type": "free"})
        else:
             # Create mode logic
             available_mb = available_gb * 1024
             if available_mb > total_required_mb:
                rem_mb = available_mb - total_required_mb
                segments.append({"name": "Free/Data", "size": rem_mb, "color": "white", "outline": "#bdc3c7", "type": "free"})

        color = "black"
        status_text = "Ready"

        # Validation Logic
        can_proceed = True
        error_msg = ""

        if self.total_required_gb > 0 or (is_update and len(selected_items) > 0):
            if available_gb > 0 or is_update:
                if not is_update:
                    # Create Mode: Total Required must fit in Total Disk
                    if self.total_required_gb > available_gb:
                        can_proceed = False
                        error_msg = "Space Insufficient!"
                    else:
                        status_text = "✅ Fits"
                else:
                    # Update Mode:
                    # 1. New partitions must fit in Free Space
                    if self.total_required_gb > available_gb:
                        can_proceed = False
                        error_msg = "Free Space Insufficient for New Items!"

                    # 2. Replacements must fit in Existing Partitions
                    # We check the segments we just built for red color
                    for seg in segments:
                        if seg['color'] == "red":
                            can_proceed = False
                            error_msg = f"'{seg['name']}' too large for existing partition!"
                            break

                    if can_proceed:
                        status_text = "✅ Update Possible"
            else:
                status_text = "Select a Disk"
        else:
            status_text = "Select Installers"

        if not can_proceed:
            color = "red"
            status_text = f"❌ {error_msg}"
            self.create_btn.config(state="disabled")
        else:
            color = "green"
            if not self.is_working and (len(selected_items) > 0): self.create_btn.config(state="normal")

        self.space_label.config(
            text=f"New Required: {self.total_required_gb:.2f} GB | Free: {available_gb:.2f} GB | {status_text}",
            foreground=color
        )
        self.draw_viz(segments, available_gb * 1024 if is_update else available_gb * 1024)

    def draw_viz(self, segments, total_capacity_mb):
        self.viz_canvas.delete("all")
        # Save segments for click handler
        self.viz_segments = segments

        if total_capacity_mb <= 0: return
        w = self.viz_canvas.winfo_width()
        h = self.viz_canvas.winfo_height()
        if w < 10: w = 900
        current_x = 0

        total_seg_size = sum(s['size'] for s in segments)
        render_max = max(total_capacity_mb, total_seg_size)
        scale = w / render_max if render_max > 0 else 1

        for i, seg in enumerate(segments):
            width = seg["size"] * scale
            outline = seg.get("outline", "white")
            tag_id = f"seg_{i}"

            self.viz_canvas.create_rectangle(
                current_x, 0, current_x + width, h,
                fill=seg["color"], outline=outline, width=1,
                tags=(tag_id, "segment")
            )

            if width > 40:
                name_short = seg['name'][:15]
                text_color = "black" if seg["color"] in ["white", "#ecf0f1", "#bdc3c7", "#50e3c2"] else "white"
                self.viz_canvas.create_text(
                    current_x + width/2, h/2,
                    text=name_short, fill=text_color, font=("Arial", 9, "bold"),
                    tags=(tag_id, "segment")
                )
            current_x += width

    def on_viz_click(self, event):
        x = self.viz_canvas.canvasx(event.x)
        y = self.viz_canvas.canvasy(event.y)
        item = self.viz_canvas.find_closest(x, y)
        tags = self.viz_canvas.gettags(item)

        for tag in tags:
            if tag.startswith("seg_"):
                idx = int(tag.split("_")[1])
                if 0 <= idx < len(self.viz_segments):
                    seg = self.viz_segments[idx]
                    installer_item = seg.get('installer_item')
                    if installer_item:
                        self.inst_tree.selection_set(installer_item)
                        self.inst_tree.see(installer_item)
                        self.inst_tree.focus(installer_item)
                    elif seg.get('type') == 'existing':
                        # Highlight in content tree
                        part_id = seg.get('id')
                        # Find item in content tree with this tag
                        for child in self.content_tree.get_children():
                            if part_id in self.content_tree.item(child, 'tags'):
                                self.content_tree.selection_set(child)
                                self.content_tree.see(child)
                                self.content_tree.focus(child)
                                break

    def refresh_hardware(self):
        self.log("Scanning hardware...")
        show_all = self.show_all_disks_var.get()
        try:
            drives = disk_detector.get_external_usb_drives(show_all=show_all)
            options = []
            if drives:
                for d in drives:
                    options.append(f"{d['name']} ({d['id']}) - {d['size_gb']:.1f} GB")
                self.disk_combo['values'] = options
                if options: self.disk_combo.current(0)
                self.log(f"Found {len(drives)} drives.")
                self.on_disk_selected(None)
            else:
                self.disk_combo['values'] = ["No external USB drives found"]
                self.disk_combo.set("No external USB drives found")
                self.log("No drives found.")
        except Exception as e:
            self.log(f"Error scanning drives: {e}")
        self.scan_installers()
        self.update_space_usage()

    def scan_installers(self):
        for item in self.inst_tree.get_children():
            self.inst_tree.delete(item)
        self.installers_list = installer_scanner.scan_for_installers()
        import detection.stub_validator
        default_buffer = self.buffer_var.get()
        if self.installers_list:
            for inst in self.installers_list:
                is_stub = detection.stub_validator.is_stub_installer(inst['path'])
                inst['is_stub'] = is_stub
                status = "STUB" if is_stub else inst.get('status', 'FULL')
                size_gb = inst['size_kb'] / (1024 * 1024)
                key = f"{inst['name']}_{inst['version']}"
                buf = self.custom_buffers.get(key, default_buffer)
                item_id = self.inst_tree.insert("", "end", values=(
                    "☐", inst['name'], inst['version'], f"{size_gb:.2f} GB", f"{buf:.1f} GB", status
                ))
                if is_stub: self.inst_tree.item(item_id, tags=("stub",))
            self.inst_tree.tag_configure("stub", foreground="gray")
            self.log(f"Found {len(self.installers_list)} local installer(s).")
        else:
            self.log("No local installers found.")
        self.update_space_usage()

    def select_all_installers(self):
        for item in self.inst_tree.get_children():
            tags = self.inst_tree.item(item, "tags")
            if "stub" not in tags:
                self.inst_tree.set(item, "Select", "☑")
        self.update_space_usage()

    def deselect_all_installers(self):
        for item in self.inst_tree.get_children():
            self.inst_tree.set(item, "Select", "☐")
        self.update_space_usage()

    def show_context_menu(self, event):
        item = self.inst_tree.identify_row(event.y)
        if item:
            self.inst_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def delete_selected_installer(self):
        selected = self.inst_tree.selection()
        if not selected: return
        if not messagebox.askyesno("Delete", f"Delete {len(selected)} installer(s)?"): return
        for item in selected:
            values = self.inst_tree.item(item)['values']
            name = values[1]
            path = None
            for inst in self.installers_list:
                if inst['name'] == name:
                    path = inst['path']
                    break
            if path:
                try:
                    subprocess.run(['sudo', 'rm', '-rf', path], check=True)
                    self.log(f"Deleted {name}")
                except subprocess.CalledProcessError as e:
                    self.log(f"Failed to delete {name}: {e}")
        self.scan_installers()

    def open_download_dialog(self):
        search = simpledialog.askstring("Download Installer", "Enter search term (e.g. 'Sonoma', '13.6', '12') [Empty for All]:")
        self.log(f"Searching Mist for '{search}'...")
        threading.Thread(target=self.run_mist_search, args=(search,)).start()

    def run_mist_search(self, search_term):
        self.create_btn.config(state="disabled")
        try:
            if not mist_downloader.check_mist_available():
                self.log("Mist-CLI missing. Attempting install...")
                mist_downloader.install_mist()
            installers = mist_downloader.list_installers(search_term)
            if not installers:
                self.log("No installers found matching that term.")
                return
            self.root.after(0, lambda: self.show_download_selection(installers))
        except Exception as e:
            self.log(f"Error searching: {e}")
        finally:
            self.root.after(0, lambda: self.create_btn.config(state="normal"))

    def show_download_selection(self, data):
        top = tk.Toplevel(self.root)
        top.title("Select Version to Download")
        top.geometry("800x500")
        cols = ("Select", "Name", "Version", "Build", "Size", "Date", "Status")
        tree = ttk.Treeview(top, columns=cols, show="headings", selectmode="extended")
        tree.heading("Select", text="[x]")
        tree.column("Select", width=40, anchor="center")
        for c in cols[1:]:
            tree.heading(c, text=c)
            if c == "Name": tree.column(c, width=200)
            else: tree.column(c, width=90)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        def on_dl_click(event):
            region = tree.identify("region", event.x, event.y)
            if region == "cell" and tree.identify_column(event.x) == "#1":
                item = tree.identify_row(event.y)
                curr = tree.set(item, "Select")
                tree.set(item, "Select", "☑" if curr == "☐" else "☐")
                return "break"
        tree.bind("<Button-1>", on_dl_click)
        for item in data:
            size_gb = f"{item.get('size', 0) / (1024**3):.1f} GB"
            status_flags = []
            if item.get('downloaded'): status_flags.append("Installed")
            if item.get('latest'): status_flags.append("Latest")
            status_str = ", ".join(status_flags)
            item_id = tree.insert("", "end", values=(
                "☐", item.get('name'), item.get('version'), item.get('build'), size_gb, item.get('date'), status_str
            ))
            if item.get('latest'): tree.item(item_id, tags=("latest",))
            if item.get('downloaded'): tree.item(item_id, tags=("installed",))
        tree.tag_configure("latest", font=("TkDefaultFont", 10, "bold"))
        tree.tag_configure("installed", foreground="gray")
        def do_download():
            selected_items = []
            for item in tree.get_children():
                if tree.set(item, "Select") == "☑":
                    vals = tree.item(item)['values']
                    name = vals[1]
                    version = str(vals[2])
                    build = str(vals[3])
                    identifier = None
                    for d in data:
                        if d.get('name') == name and d.get('version') == version and d.get('build') == build:
                            identifier = d.get('identifier')
                            break
                    selected_items.append((identifier, name))
            if not selected_items: return
            top.destroy()
            threading.Thread(target=self.run_download_process, args=(selected_items,)).start()
        btn = ttk.Button(top, text="Download Selected", command=do_download)
        btn.pack(pady=10)

    def run_download_process(self, items):
        self.create_btn.config(state="disabled")
        try:
            for identifier, name in items:
                self.log(f"Downloading {name}...")
                success = False
                if identifier:
                    if mist_downloader.download_installer_by_identifier(identifier, name):
                         success = True

                if not success:
                    self.log(f"ID download failed/missing, retrying with name '{name}'...")
                    if mist_downloader.download_installer([name]):
                        success = True
                    else:
                        simple_name = name.replace("OS X ", "").replace("macOS ", "").replace("Mac ", "")
                        self.log(f"Retrying with simplified name '{simple_name}'...")
                        if mist_downloader.download_installer([simple_name]):
                            success = True

                if success:
                    self.log(f"Download of {name} complete.")
                else:
                    self.log(f"Download of {name} failed.")
            self.root.after(0, self.scan_installers)
        except Exception as e:
            self.log(f"Download error: {e}")
        finally:
            self.root.after(0, lambda: self.create_btn.config(state="normal"))

    def format_disk_dialog(self):
        disk_str = self.selected_disk.get()
        if not disk_str: return
        disk_id = disk_str.split('(')[1].split(')')[0]
        if messagebox.askyesno("Format", f"Erase {disk_id}?"):
             threading.Thread(target=self.run_format_disk, args=(disk_id,)).start()

    def run_format_disk(self, disk_id):
        self.log(f"Formatting {disk_id}...")
        try:
            subprocess.run(['diskutil', 'eraseDisk', 'JHFS+', 'UNTITLED', disk_id], check=True)
            self.log("Format complete.")
            self.root.after(0, self.refresh_hardware)
        except Exception as e:
            self.log(f"Format failed: {e}")

    def start_creation(self):
        selected_items = self.get_selected_installers()
        if not selected_items:
            messagebox.showwarning("Warning", "Select an installer.")
            return
        disk_str = self.selected_disk.get()
        if not disk_str: return
        try: disk_id = disk_str.split('(')[1].split(')')[0]
        except: return

        target_installers = []
        for item_id in selected_items:
            values = self.inst_tree.item(item_id)['values']
            name = values[1]
            version = str(values[2])
            buffer_val = float(values[4].split()[0])
            found = None
            for inst in self.installers_list:
                if inst['name'] == name and str(inst['version']) == version:
                    found = inst.copy()
                    found['buffer_gb'] = buffer_val
                    break
            if found: target_installers.append(found)
        if not target_installers: return

        if self.update_mode_var.get():
            if messagebox.askyesno("Confirm Update", f"Update {disk_id}?\n\nThis will look for free space or existing partitions to replace.\nEXISTING INSTALLERS (NOT SELECTED) WILL NOT BE ERASED."):
                self.log("Starting Update Process...")
                self.create_btn.config(state="disabled")
                self.is_working = True
                threading.Thread(target=self.run_update_thread, args=(disk_id, target_installers)).start()
        else:
            if messagebox.askyesno("Confirm Erase", f"Erase {disk_id} and install {len(target_installers)} macOS versions?\n\nALL DATA WILL BE LOST."):
                self.log("Starting Creation Process...")
                self.create_btn.config(state="disabled")
                self.is_working = True
                threading.Thread(target=self.run_creation_thread, args=(disk_id, target_installers)).start()

    def run_update_thread(self, disk_id, installers):
        try:
            import operations.updater
            import operations.installer_runner
            import operations.branding
            import core.constants

            self.log(f"Analyzing {disk_id}...")
            structure = operations.updater.get_drive_structure(disk_id)
            if not structure:
                self.log("Failed to analyze drive.")
                return

            actions = []
            existing_map = structure.get('existing_installers', {})

            for inst in installers:
                new_os_name = core.constants.get_os_name(inst['version'], inst['name'])
                match_id = None
                if new_os_name in existing_map:
                    match_id = existing_map[new_os_name]
                else:
                    for key, pid in existing_map.items():
                        if new_os_name in key:
                            match_id = pid
                            break
                if match_id:
                    self.log(f"Found existing {new_os_name} at {match_id}. Will replace.")
                    actions.append({'type': 'replace', 'installer': inst, 'target': match_id})
                else:
                    self.log(f"{new_os_name} not found. Will add to free space.")
                    actions.append({'type': 'add', 'installer': inst})

            for action in actions:
                inst = action['installer']
                if action['type'] == 'replace':
                    target = action['target']
                    res = operations.updater.replace_existing_partition(target, inst)
                    if res:
                        part_name = res['name']
                    else:
                        self.log(f"Failed to prepare partition for {inst['name']}")
                        continue
                elif action['type'] == 'add':
                    res_list = operations.updater.add_partition_to_free_space(disk_id, [inst])
                    if res_list:
                        part_name = res_list[0]['name']
                    else:
                        self.log(f"Failed to add partition for {inst['name']}")
                        continue

                self.log(f"Installing {inst['name']} to {part_name}...")
                subprocess.run(['diskutil', 'mount', part_name])
                mount_point = f"/Volumes/{part_name}"
                if not os.path.exists(mount_point): time.sleep(3)

                if os.path.exists(mount_point):
                    def cb(p):
                        if p%10==0: self.log(f"  {inst['name']}: {p}%")
                    if operations.installer_runner.run_createinstallmedia(inst['path'], mount_point, progress_callback=cb):
                        self.log("Success.")
                        std_name = f"/Volumes/Install {inst['name'].replace('.app','')}"
                        if not os.path.exists(std_name): std_name = mount_point
                        os_name = core.constants.get_os_name(inst['version'], inst['name'])
                        operations.branding.apply_full_branding(std_name, inst['name'], os_name, inst['version'])
                    else:
                        self.log("Installation failed.")
                else:
                    self.log(f"Could not mount {part_name}")

            if structure['free_space'] > 2e9:
                structure_new = operations.updater.get_drive_structure(disk_id)
                if structure_new and structure_new['free_space'] > 2e9:
                    self.log("Restoring unused space to DATA_STORE...")
                    operations.updater.restore_data_partition(disk_id)

            self.log("Update Complete.")
            self.root.after(0, lambda: messagebox.showinfo("Success", "Update Complete"))

        except Exception as e:
            self.log(f"Error: {e}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.is_working = False
            self.root.after(0, lambda: self.create_btn.config(state="normal"))

    def run_creation_thread(self, disk_id, installers):
        try:
            import safety.backup_manager
            safety.backup_manager.backup_partition_table(disk_id)
            for inst in installers:
                branding.extract_icon_from_installer(inst['path'], inst['name'])
            import operations.updater
            struct = operations.updater.get_drive_structure(disk_id)
            total_size_gb = struct['disk_size'] / 1e9 if struct else 0
            self.log(f"Partitioning {disk_id}...")
            success = partitioner.create_multiboot_layout(disk_id, installers, total_size_gb)
            if not success:
                self.log("Partitioning failed.")
                return
            time.sleep(5)
            current_partitions = partitioner.get_partition_list(disk_id)
            for inst in installers:
                self.log(f"Installing {inst['name']}...")
                os_name = constants.get_os_name(inst['version'], inst['name'])
                version_clean = inst['version'].replace('.', '_').split()[0]
                expected_vol_name = f"INSTALL_{os_name}_{version_clean}"[:27]
                target_part = next((p for p in current_partitions if p['name'] == expected_vol_name), None)
                if not target_part:
                    time.sleep(2)
                    current_partitions = partitioner.get_partition_list(disk_id)
                    target_part = next((p for p in current_partitions if p['name'] == expected_vol_name), None)
                if target_part:
                    part_id = target_part['id']
                    part_num = part_id.replace(disk_id, '').replace('s', '')
                    mount_point = installer_runner.get_volume_mount_point(disk_id, part_num)
                    if not mount_point:
                        subprocess.run(['diskutil', 'mount', part_id])
                        time.sleep(1)
                        mount_point = installer_runner.get_volume_mount_point(disk_id, part_num)
                    if mount_point:
                        def cb(p):
                            if p%10==0: self.log(f"  {inst['name']}: {p}%")
                        if installer_runner.run_createinstallmedia(inst['path'], mount_point, progress_callback=cb):
                            self.log("Success.")
                            new_mount = installer_runner.get_volume_mount_point(disk_id, part_num)
                            if new_mount: branding.apply_full_branding(new_mount, inst['name'], os_name, inst['version'])
                        else:
                            self.log("Failed.")
            self.log("Done.")
            self.root.after(0, lambda: messagebox.showinfo("Success", "Complete"))
        except Exception as e:
            self.log(f"Error: {e}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.is_working = False
            self.root.after(0, lambda: self.create_btn.config(state="normal"))

def launch(config=None):
    if os.geteuid() != 0:
        print("Warning: Running GUI without root.")
    root = tk.Tk()
    app = MultiBootGUI(root, config)
    root.mainloop()

if __name__ == "__main__":
    launch()
