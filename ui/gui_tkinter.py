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

# Import modular components
from ui.components.disk_selector import DiskSelector
from ui.components.installer_tree import InstallerTree
from ui.components.status_panel import StatusPanel
from ui.components.action_panel import ActionPanel
from ui.components.visualization_canvas import VisualizationCanvas

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
        self.disk_selector = DiskSelector(
            top_frame,
            on_disk_selected=self.on_disk_selected,
            show_all_var=self.show_all_disks_var,
            refresh_command=self.refresh_hardware
        )
        self.disk_selector.pack(fill="x", padx=5, pady=5)

        # Add explicit Mode Radiobuttons to the Disk Selector's mode_frame
        ttk.Label(self.disk_selector.mode_frame, text="Operation Mode:", font=("Arial", 9, "bold")).pack(side="left", padx=(0, 5))

        self.mode_rb_create = ttk.Radiobutton(
            self.disk_selector.mode_frame, text="Create (Erase All)",
            variable=self.mode_var, value="create", command=self.on_mode_change
        )
        self.mode_rb_create.pack(side="left", padx=5)

        self.mode_rb_update = ttk.Radiobutton(
            self.disk_selector.mode_frame, text="Update (Keep Data)",
            variable=self.mode_var, value="update", command=self.on_mode_change
        )
        self.mode_rb_update.pack(side="left", padx=5)

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
        self.installer_tree_frame = InstallerTree(
            top_frame,
            on_click=self.on_tree_click,
            on_double_click=self.on_tree_double_click,
            on_right_click=self.show_context_menu,
            apply_filter_command=self.apply_filter
        )
        self.installer_tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.inst_tree = self.installer_tree_frame.tree
        self.filter_var = self.installer_tree_frame.filter_var
        self.search_var = self.installer_tree_frame.search_var

        # Bind Installer Tree Buttons
        self.installer_tree_frame.select_all_btn.config(command=self.select_all_installers)
        self.installer_tree_frame.unselect_all_btn.config(command=self.deselect_all_installers)
        self.installer_tree_frame.delete_local_btn.config(command=self.delete_selected_installer)
        self.installer_tree_frame.refresh_btn.config(command=self.scan_installers)

        # Bind Spacebar to toggle selection
        self.inst_tree.bind("<space>", self.on_space_press)

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

        # Auto-Download Options
        dl_frame = ttk.Frame(settings_frame)
        dl_frame.pack(fill="x", padx=5, pady=2)

        self.auto_dl_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dl_frame, text="Auto-download missing installers", variable=self.auto_dl_var, command=self.update_space_usage).pack(side="left", padx=5)

        self.dl_size_label = ttk.Label(dl_frame, text="", foreground="blue")
        self.dl_size_label.pack(side="left", padx=10)

        self.space_label = ttk.Label(settings_frame, text="Required: 0.0 GB | Available: 0.0 GB | Select Installers & Disk", font=("Arial", 10, "bold"))
        self.space_label.pack(fill="x", padx=10, pady=10)

        self.viz_canvas = VisualizationCanvas(settings_frame, self.on_viz_click)
        self.viz_canvas.pack(fill="x", padx=10, pady=5)

        # Action Panel
        self.action_panel = ActionPanel(bottom_frame, self.start_creation)
        self.action_panel.pack(fill="x")
        self.create_btn = self.action_panel.create_btn

        # Status Panel
        self.status_panel = StatusPanel(bottom_frame)
        self.status_panel.pack(fill="both", expand=True, padx=5, pady=5)

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
            # Pack after the disk_selector frame
            self.content_frame.pack(fill="both", expand=True, padx=5, pady=5, after=self.disk_selector)
            self.on_disk_selected(None)
        else:
            self.create_btn.config(text="CREATE BOOTABLE USB (Erase All)")
            self.content_frame.pack_forget()
        self.update_space_usage()

    def on_tree_click(self, event):
        region = self.inst_tree.identify("region", event.x, event.y)
        if region == "cell":
            # The click event fires before Treeview updates its selection.
            # Using after(10) ensures we act on the updated state if needed,
            # but for simple toggling based on row ID, we can do it immediately.
            item_id = self.inst_tree.identify_row(event.y)
            if item_id:
                # Toggle selection state
                self.toggle_selection(item_id)

    def on_tree_double_click(self, event):
        item_id = self.inst_tree.identify_row(event.y)
        if item_id:
            self.edit_selected_buffer(item_id)

    def on_space_press(self, event):
        items = self.inst_tree.selection()
        if not items: return
        for item in items:
            self.toggle_selection(item)
        return "break"

    def toggle_selection(self, item_id):
        if not item_id: return
        tags = self.inst_tree.item(item_id, "tags")
        if "stub" in tags:
            return # Silent fail for spacebar bulk toggle

        current = self.inst_tree.set(item_id, "Select")
        is_checked = current in ["☑", "[x]", "YES", "✓"]
        new_val = "[ ]" if is_checked else "[x]"

        self.inst_tree.set(item_id, "Select", new_val)

        # Defer space calculation to prevent blocking the UI thread during rapid clicks
        if hasattr(self, '_update_space_timer'):
            self.root.after_cancel(self._update_space_timer)
        self._update_space_timer = self.root.after(100, self.update_space_usage)

    def edit_selected_buffer(self, item_id=None):
        if not item_id:
            sel = self.inst_tree.selection()
            if sel: item_id = sel[0]
            else: return
        values = self.inst_tree.item(item_id)['values']
        name = values[1]
        # Buffer is index 5
        try:
            current_buffer = values[5]
        except IndexError:
            current_buffer = "2.0 GB"

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
                self.status_panel.log(msg)
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
        self.log(f"Scanning content of {disk_id}...")
        structure = updater.get_drive_structure(disk_id)
        if structure:
            self.existing_installers_map = structure.get('existing_installers', {})
            self.drive_structure = structure # Store full structure

            # Auto-Detect Mode
            existing = structure.get('existing_partitions', [])
            if existing:
                self.mode_var.set("update")
            else:
                self.mode_var.set("create")

            self.root.after(0, self.on_mode_change)
            self.root.after(0, lambda: self.update_content_ui(structure))
            self.root.after(0, self.update_space_usage)
            self.log(f"Found {len(existing)} existing partitions.")
        else:
            self.log(f"Failed to read structure for {disk_id}.")
            self.drive_structure = None
            self.existing_installers_map = {}
            self.root.after(0, lambda: self.update_content_ui({'existing_partitions': []}))
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
            val = self.inst_tree.set(item, "Select")
            if val in ["☑", "[x]", "YES", "✓"]:
                selected.append(item)
        return selected

    def update_space_usage(self, event=None):
        selected_items = self.get_selected_installers()
        is_update = self.mode_var.get() == "update"

        total_download_kb = 0
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

            # Use tags for quick lookup of size
            size_kb = 0
            tags = self.inst_tree.item(item_id, "tags")
            if tags and tags[0].isdigit():
                idx = int(tags[0])
                if idx < len(self.installers_list):
                    size_kb = self.installers_list[idx]['size_kb']

            if size_kb == 0:
                for inst in self.installers_list:
                    if inst['name'] == name and str(inst['version']) == version:
                        size_kb = inst['size_kb']
                        break

            # Check download requirement
            # If source is remote (via values[6] which is icon, or logic), add to download
            # values[6] is Source Icon. ☁️ means remote.
            if "☁️" in values[6]:
                total_download_kb += size_kb

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

            try: buffer_gb = float(values[5].split()[0])
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
                    # In update mode, available for NEW partitions is just Free Space + DATA_STORE size
                    free_gb = self.drive_structure['free_space'] / 1e9
                    data_part = self.drive_structure.get('data_partition')
                    if data_part:
                        free_gb += data_part['size'] / 1e9
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
             segments.append({"name": "Free/Data", "size": free_mb, "color": "white", "outline": "#bdc3c7", "type": "free"})
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
                        if seg['color'] == "#e74c3c": # Red
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
            self.create_btn.config(state="disabled", text="CANNOT PROCEED (Space Issue)")
        else:
            color = "green"
            if not self.is_working and (len(selected_items) > 0):
                self.create_btn.config(state="normal")
                # Smart Button Text
                btn_text = "CREATE NEW USB"
                if is_update: btn_text = "UPDATE EXISTING USB"

                if total_download_kb > 0:
                    dl_gb = total_download_kb / (1024*1024)
                    btn_text = f"DOWNLOAD ({dl_gb:.1f}GB) & {btn_text}"

                self.create_btn.config(text=btn_text)

        self.space_label.config(
            text=f"New Required: {self.total_required_gb:.2f} GB | Free: {available_gb:.2f} GB | {status_text}",
            foreground=color
        )

        if total_download_kb > 0:
            dl_gb = total_download_kb / (1024*1024)
            self.dl_size_label.config(text=f"📥 Download Required: {dl_gb:.1f} GB")
        else:
            self.dl_size_label.config(text="")

        self.viz_canvas.draw_segments(segments, available_gb * 1024 if is_update else available_gb * 1024)

    def on_viz_click(self, event):
        x = self.viz_canvas.canvasx(event.x)
        y = self.viz_canvas.canvasy(event.y)
        item = self.viz_canvas.find_closest(x, y)
        tags = self.viz_canvas.gettags(item)

        # Access segments from the canvas component
        segments = self.viz_canvas.viz_segments

        for tag in tags:
            if tag.startswith("seg_"):
                idx = int(tag.split("_")[1])
                if 0 <= idx < len(segments):
                    seg = segments[idx]
                    installer_item = seg.get('installer_item')
                    if installer_item:
                        self.inst_tree.selection_set(installer_item)
                        self.inst_tree.see(installer_item)
                        self.inst_tree.focus(installer_item)
                        # Open buffer editor on click if it's a new item
                        if seg.get('type') == 'new' or seg.get('type') == 'replacing':
                             self.edit_selected_buffer(installer_item)
                    elif seg.get('type') == 'existing':
                        # Highlight in content tree
                        part_id = seg.get('id')
                        for child in self.content_tree.get_children():
                            if part_id in self.content_tree.item(child, 'tags'):
                                self.content_tree.selection_set(child)
                                self.content_tree.see(child)
                                self.content_tree.focus(child)
                                break

    def refresh_hardware(self):
        self.log("Scanning hardware...")
        # Delegate to DiskSelector (Async)
        self.disk_selector.update_disks()

        # Scan installers (Async)
        self.scan_installers()
        self.update_space_usage()

    def scan_installers(self):
        self.log("Scanning for installers (Local + Remote)...")
        # Clear tree
        for item in self.inst_tree.get_children():
            self.inst_tree.delete(item)

        # Run in thread
        threading.Thread(target=self._scan_installers_thread).start()

    def _scan_installers_thread(self):
        # 1. Local Scan
        local_list = installer_scanner.scan_for_installers()
        import detection.stub_validator

        # Enhance local list
        for inst in local_list:
            inst['source'] = 'local'
            inst['is_stub'] = detection.stub_validator.is_stub_installer(inst['path'])
            inst['status'] = "STUB" if inst['is_stub'] else "Ready"
            inst['identifier'] = None # Local ones might not have identifiers easily

        # 2. Remote Scan (Mist)
        remote_list = []
        if mist_downloader.check_mist_available():
            try:
                remote_list = mist_downloader.list_installers() # Returns list of dicts
            except Exception as e:
                self.log(f"Mist error: {e}")

        # 3. Merge Lists
        # Use (version, build) as key
        merged_map = {}

        # Add Remote first
        for r in remote_list:
            key = (r.get('version'), r.get('build'))
            r['source'] = 'remote'
            r['path'] = None
            r['status'] = "Available"
            r['size_kb'] = r.get('size', 0) / 1024 # Convert bytes to KB
            merged_map[key] = r

        # Add Local (overwriting remote if exists, or adding new)
        for l in local_list:
            # Try to get build number if possible, or just version
            # Local scanner might not get build number perfectly.
            # If we don't have build, we rely on version.
            # But remote usually has build.
            # Simple approach: Match by Name + Version
            matched = False
            l_clean = l['name'].replace("Install ", "").replace(".app", "")
            for k, v in merged_map.items():
                v_clean = v['name'].replace("Install ", "").replace(".app", "")
                if v['version'] == str(l['version']) and (v['name'] == l['name'] or v_clean == l_clean):
                    # Update existing remote entry to be local
                    v['source'] = 'local'
                    v['path'] = l['path']
                    v['status'] = "Downloaded"
                    v['is_stub'] = l['is_stub']
                    if l['is_stub']: v['status'] = "STUB (Local)"
                    v['size_kb'] = l['size_kb'] # Use local size
                    matched = True
                    break

            if not matched:
                # Add as local-only
                key = (l['version'], 'local')
                merged_map[key] = l

        # Convert back to list and sort
        final_list = list(merged_map.values())
        # Sort by version desc
        try:
            final_list.sort(key=lambda x: x.get('version', '0'), reverse=True)
        except: pass

        self.installers_list = final_list
        self.root.after(0, self.apply_filter)
        self.root.after(0, lambda: self.log(f"Found {len(final_list)} installers (Local+Remote)."))

    def apply_filter(self):
        # Clear current view
        for item in self.inst_tree.get_children():
            self.inst_tree.delete(item)

        filter_mode = self.filter_var.get()
        search_term = self.search_var.get().lower()

        count = 0
        for inst in self.installers_list:
            # 1. Filter by Mode
            if filter_mode == "local" and inst['source'] != 'local': continue
            if filter_mode == "remote" and inst['source'] != 'remote': continue

            # 2. Filter by Search
            name_ver = f"{inst['name']} {inst['version']}".lower()
            if search_term and search_term not in name_ver: continue

            # Add to tree
            size_gb = inst['size_kb'] / (1024 * 1024)
            source_icon = "💻" if inst['source'] == 'local' else "☁️"

            # Determine buffer
            default_buffer = self.buffer_var.get()
            key = f"{inst['name']}_{inst['version']}"
            buf = self.custom_buffers.get(key, default_buffer)

            values = (
                "[ ]",
                inst['name'],
                inst['version'],
                inst.get('build', ''),
                f"{size_gb:.2f} GB",
                f"{buf:.1f} GB",
                source_icon,
                inst['status']
            )

            item_id = self.inst_tree.insert("", "end", values=values)

            # Store full data ref
            # We need to map item_id to index in self.installers_list or store data
            # Simplest is to rely on values, but source is icon now.
            # Let's store index in tags
            self.inst_tree.item(item_id, tags=(str(self.installers_list.index(inst)),))

            tags = [str(self.installers_list.index(inst))]

            if inst.get('source') == 'local':
                tags.append("local")
            else:
                tags.append("remote")

            if inst.get('is_stub'):
                tags.append("stub")

            self.inst_tree.item(item_id, tags=tuple(tags))
            count += 1

        # Configure Visual Styles
        self.inst_tree.tag_configure("local", font=("TkDefaultFont", 10, "bold"), foreground="black")
        self.inst_tree.tag_configure("remote", foreground="#555555")
        self.inst_tree.tag_configure("stub", foreground="gray", font=("TkDefaultFont", 10, "italic"))
        self.update_space_usage()

    def select_all_installers(self):
        for item in self.inst_tree.get_children():
            tags = self.inst_tree.item(item, "tags")
            # Only select if not stub. Remote is fine.
            if "stub" not in tags:
                self.inst_tree.set(item, "Select", "[x]")
        self.update_space_usage()

    def deselect_all_installers(self):
        for item in self.inst_tree.get_children():
            self.inst_tree.set(item, "Select", "[ ]")
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
                is_checked = curr in ["☑", "[x]"]
                tree.set(item, "Select", "[ ]" if is_checked else "[x]")
                # Allow default selection
                pass

        tree.bind("<Button-1>", on_dl_click)
        for item in data:
            size_gb = f"{item.get('size', 0) / (1024**3):.1f} GB"
            status_flags = []
            if item.get('downloaded'): status_flags.append("Installed")
            if item.get('latest'): status_flags.append("Latest")
            status_str = ", ".join(status_flags)
            item_id = tree.insert("", "end", values=(
                "[ ]", item.get('name'), item.get('version'), item.get('build'), size_gb, item.get('date'), status_str
            ))
            if item.get('latest'): tree.item(item_id, tags=("latest",))
            if item.get('downloaded'): tree.item(item_id, tags=("installed",))
        tree.tag_configure("latest", font=("TkDefaultFont", 10, "bold"))
        tree.tag_configure("installed", foreground="gray")
        def do_download():
            selected_items = []
            for item in tree.get_children():
                val = tree.set(item, "Select")
                if val in ["☑", "[x]"]:
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
        if not selected_items: return

        disk_str = self.selected_disk.get()
        if not disk_str: return
        try: disk_id = disk_str.split('(')[1].split(')')[0]
        except: return

        target_installers = []
        download_list = []

        for item_id in selected_items:
            values = self.inst_tree.item(item_id)['values']
            buffer_val = float(values[5].split()[0])
            found = None

            tags = self.inst_tree.item(item_id, "tags")
            if tags and tags[0].isdigit():
                idx = int(tags[0])
                if idx < len(self.installers_list):
                    found = self.installers_list[idx].copy()
                    found['buffer_gb'] = buffer_val

            if found:
                target_installers.append(found)
                if found.get('source') == 'remote':
                    download_list.append(found)

        if download_list and not self.auto_dl_var.get():
            messagebox.showwarning("Missing Installers", "You have selected remote installers but auto-download is disabled.")
            return

        self.show_preflight_dialog(disk_id, target_installers, download_list)

    def show_preflight_dialog(self, disk_id, installers, download_list):
        top = tk.Toplevel(self.root)
        top.title("Pre-Flight Summary")
        top.geometry("600x500")

        ttk.Label(top, text="Ready to prepare your multi-boot USB", font=("Arial", 14, "bold")).pack(pady=10)

        # Summary
        summary_frame = ttk.LabelFrame(top, text="Plan of Action")
        summary_frame.pack(fill="both", expand=True, padx=10, pady=5)

        text_area = tk.Text(summary_frame, height=15, width=60, font=("Arial", 11))
        text_area.pack(fill="both", expand=True, padx=5, pady=5)

        summary = []
        summary.append(f"Target Disk: {disk_id}")
        summary.append(f"Mode: {self.mode_var.get().upper()}")
        summary.append("-" * 40)

        if download_list:
            total_dl = sum(i['size_kb'] for i in download_list) / (1024*1024)
            summary.append(f"📥 Download: {len(download_list)} installers ({total_dl:.1f} GB)")
            for dl in download_list:
                summary.append(f"   • {dl['name']} {dl['version']}")
            summary.append("")

        summary.append(f"💾 Installation: {len(installers)} versions")
        for inst in installers:
            action = "Install"
            if inst.get('source') == 'remote': action = "Download & Install"
            summary.append(f"   • {inst['name']} {inst['version']} ({action})")

        if self.mode_var.get() == "create":
            summary.append("\n⚠️ WARNING: DISK WILL BE COMPLETELY ERASED!")

        text_area.insert("end", "\n".join(summary))
        text_area.config(state="disabled")

        btn_frame = ttk.Frame(top)
        btn_frame.pack(fill="x", pady=10)

        def on_confirm():
            top.destroy()
            self.run_full_process(disk_id, installers, download_list)

        ttk.Button(btn_frame, text="Cancel", command=top.destroy).pack(side="right", padx=10)
        ttk.Button(btn_frame, text="PROCEED", command=on_confirm).pack(side="right", padx=10)

    def run_full_process(self, disk_id, installers, download_list):
        self.create_btn.config(state="disabled")
        self.is_working = True

        def process_thread():
            # 1. Download Phase
            if download_list:
                self.log("=== Phase 1: Downloading Missing Installers ===")
                items_to_dl = []
                for d in download_list:
                    items_to_dl.append((d.get('identifier'), d['name']))

                # Use existing logic but synchronously here
                self.run_download_process_sync(items_to_dl)

                # Re-scan to update paths?
                # Actually, run_download_process updates scanner.
                # But we have 'installers' list with OLD paths (None).
                # We need to refresh 'installers' paths.
                self.log("Refreshing installer paths...")
                new_scan = installer_scanner.scan_for_installers()
                for inst in installers:
                    if inst['source'] == 'remote':
                        # Find matching local
                        for local in new_scan:
                            if local['name'] == inst['name'] and str(local['version']) == str(inst['version']):
                                inst['path'] = local['path']
                                inst['source'] = 'local'
                                break
                        if not inst.get('path'):
                            self.log(f"❌ Failed to verify download for {inst['name']}")
                            self.is_working = False
                            self.root.after(0, lambda: self.create_btn.config(state="normal"))
                            return

            # 2. Creation/Update Phase
            self.log(f"=== Phase 2: {self.mode_var.get().upper()} Process ===")
            if self.mode_var.get() == "update":
                self.run_update_thread_logic(disk_id, installers)
            else:
                self.run_creation_thread_logic(disk_id, installers)

        threading.Thread(target=process_thread).start()

    def run_download_process_sync(self, items):
        # Synchronous version of run_download_process logic
        self.status_panel.set_phase("Downloading")
        try:
            total_items = len(items)
            for idx, (identifier, name) in enumerate(items):
                self.log(f"Downloading {name} ({idx+1}/{total_items})...")
                success = False

                def progress_cb(percent, msg):
                    # Update status panel progress bar
                    self.status_panel.main_progress['value'] = percent
                    self.status_panel.status_label.config(text=msg)
                    self.root.update_idletasks()

                if identifier:
                    if mist_downloader.download_installer_by_identifier(identifier, name, progress_callback=progress_cb):
                         success = True

                if not success:
                    self.log(f"ID download failed, retrying with name '{name}'...")
                    if mist_downloader.download_installer([name]): success = True

                if success: self.log(f"✓ Downloaded {name}")
                else: self.log(f"❌ Download failed for {name}")

            self.status_panel.main_progress['value'] = 0
            self.status_panel.status_label.config(text="Downloads Complete")

        except Exception as e:
            self.log(f"Download error: {e}")

    # Logic Wrappers
    def run_update_thread_logic(self, disk_id, installers):
        self.run_update_thread(disk_id, installers)

    def run_creation_thread_logic(self, disk_id, installers):
        self.run_creation_thread(disk_id, installers)

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
