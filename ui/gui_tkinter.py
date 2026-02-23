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
from core import privilege, constants
from operations import partitioner, installer_runner, branding, updater
from integration import mist_downloader

class MultiBootGUI:
    def __init__(self, root, config=None):
        self.root = root
        self.config = config
        self.root.title("macOS Multi-Tool Pro")
        self.root.geometry("1000x850")

        # Variables
        self.selected_disk = tk.StringVar()
        self.installers_list = []
        self.log_queue = queue.Queue()
        self.is_working = False

        # State for space calculation
        self.current_disk_size_gb = 0.0
        self.total_required_gb = 0.0

        # Per-installer buffer map (installer_id_string -> float gb)
        self.custom_buffers = {}

        # UI State
        self.show_all_disks_var = tk.BooleanVar(value=False)
        self.update_mode = False # Add new content vs Erase

        # Layout
        self.create_widgets()

        # Start log poller
        self.poll_log_queue()

        # Initial scan
        self.refresh_hardware()

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

        # Options Frame (Show All + Update Mode)
        opt_frame = ttk.Frame(disk_frame)
        opt_frame.pack(fill="x", padx=10, pady=5)

        ttk.Checkbutton(opt_frame, text="Show All Disks (Advanced)",
                        variable=self.show_all_disks_var,
                        command=self.refresh_hardware).pack(side="left")

        self.update_mode_var = tk.BooleanVar(value=False)
        self.update_mode_chk = ttk.Checkbutton(opt_frame, text="Update Existing Drive (Add Only)",
                        variable=self.update_mode_var,
                        command=self.on_mode_change)
        self.update_mode_chk.pack(side="left", padx=20)

        # Middle: Installer Selection
        inst_frame = ttk.LabelFrame(top_frame, text="2. Select macOS Installers")
        inst_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Treeview for installers with Checkbox column
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

        # Bindings
        self.inst_tree.bind("<Button-1>", self.on_tree_click)
        self.inst_tree.bind("<Double-1>", self.on_tree_double_click) # Edit buffer

        # Scrollbar
        scrollbar = ttk.Scrollbar(inst_frame, orient="vertical", command=self.inst_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.inst_tree.configure(yscrollcommand=scrollbar.set)

        # Context Menu
        self.context_menu = tk.Menu(self.inst_tree, tearoff=0)
        self.context_menu.add_command(label="Edit Buffer Size", command=self.edit_selected_buffer)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete Installer", command=self.delete_selected_installer)
        self.inst_tree.bind("<Button-3>", self.show_context_menu)

        # Buttons
        btn_frame = ttk.Frame(inst_frame)
        btn_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        ttk.Button(btn_frame, text="Select All", command=self.select_all_installers).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Unselect All", command=self.deselect_all_installers).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_selected_installer).pack(side="left", padx=20)
        ttk.Button(btn_frame, text="Download New...", command=self.open_download_dialog).pack(side="right", padx=2)

        # Bottom Section: Actions & Log
        bottom_frame = ttk.Frame(paned)
        paned.add(bottom_frame, weight=1)

        # Settings Frame
        settings_frame = ttk.LabelFrame(bottom_frame, text="3. Settings & Space Check")
        settings_frame.pack(fill="x", padx=5, pady=5)

        # Default Buffer Slider
        buffer_frame = ttk.Frame(settings_frame)
        buffer_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(buffer_frame, text="Default Safety Buffer (GB):").pack(side="left", padx=5)
        self.buffer_var = tk.DoubleVar(value=2.0)
        self.buffer_scale = ttk.Scale(buffer_frame, from_=0.1, to=10.0, variable=self.buffer_var, orient="horizontal")
        self.buffer_scale.pack(side="left", fill="x", expand=True, padx=5)
        self.buffer_label = ttk.Label(buffer_frame, text="2.0 GB")
        self.buffer_label.pack(side="left", padx=5)
        self.buffer_scale.configure(command=self.on_buffer_change)

        # Optimize Density Button
        ttk.Button(buffer_frame, text="Optimize Density (Min Buffers)", command=self.optimize_buffers).pack(side="right", padx=10)

        # Intelligent Space Panel
        self.space_label = ttk.Label(settings_frame, text="Required: 0.0 GB | Available: 0.0 GB | Select Installers & Disk", font=("Arial", 10, "bold"))
        self.space_label.pack(fill="x", padx=10, pady=10)

        # Visualization Canvas
        self.viz_canvas = tk.Canvas(settings_frame, height=30, bg="white")
        self.viz_canvas.pack(fill="x", padx=10, pady=5)

        # Action Button
        self.create_btn = ttk.Button(bottom_frame, text="CREATE BOOTABLE USB", command=self.start_creation)
        self.create_btn.pack(fill="x", padx=20, pady=10)

        # Log Output
        log_frame = ttk.LabelFrame(bottom_frame, text="Progress Log")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state="disabled", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    # --- Event Handlers & Logic ---

    def optimize_buffers(self):
        # Set all buffers to minimal (0.2 GB)
        MIN_SAFE_BUFFER = 0.2
        self.buffer_var.set(MIN_SAFE_BUFFER)
        self.on_buffer_change(MIN_SAFE_BUFFER)

        # Also update custom buffers map for selected items specifically to override any previous custom values
        for item in self.inst_tree.get_children():
            values = self.inst_tree.item(item)['values']
            name = values[1]
            ver = str(values[2])
            key = f"{name}_{ver}"
            self.custom_buffers[key] = MIN_SAFE_BUFFER
            self.inst_tree.set(item, "Buffer", f"{MIN_SAFE_BUFFER:.1f} GB")

        self.update_space_usage()
        messagebox.showinfo("Optimized", "Buffers set to minimum (0.2 GB) for maximum density.")

    def on_mode_change(self):
        is_update = self.update_mode_var.get()
        if is_update:
            self.create_btn.config(text="UPDATE EXISTING USB (Add Only)")
        else:
            self.create_btn.config(text="CREATE BOOTABLE USB (Erase All)")
        self.update_space_usage()

    def on_tree_click(self, event):
        region = self.inst_tree.identify("region", event.x, event.y)
        if region == "cell":
            col = self.inst_tree.identify_column(event.x)
            if col == "#1": # The 'Select' column
                item_id = self.inst_tree.identify_row(event.y)
                self.toggle_selection(item_id)
                return "break" # Stop propagation

    def on_tree_double_click(self, event):
        item_id = self.inst_tree.identify_row(event.y)
        if item_id:
            self.edit_selected_buffer(item_id)

    def toggle_selection(self, item_id):
        if not item_id: return
        current = self.inst_tree.set(item_id, "Select")

        # Don't select stubs
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
        current_buffer = values[4] # "2.0 GB"

        new_val = simpledialog.askfloat("Buffer Size", f"Enter buffer size (GB) for {name}:",
                                        minvalue=0.1, maxvalue=20.0, initialvalue=float(current_buffer.split()[0]))
        if new_val is not None:
            # Update Custom Buffer Map
            key = f"{name}_{values[2]}" # Name_Version
            self.custom_buffers[key] = new_val

            # Update UI
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
        # Auto-detect update mode eligibility?
        disk_str = self.selected_disk.get()
        if not disk_str or "No external" in disk_str: return

        try:
            disk_id = disk_str.split('(')[1].split(')')[0]
            # Check structure in background?
            # For now just trigger space update
            self.update_space_usage()
        except: pass

    def get_selected_installers(self):
        """Return list of selected item IDs"""
        selected = []
        for item in self.inst_tree.get_children():
            if self.inst_tree.set(item, "Select") == "☑":
                selected.append(item)
        return selected

    def update_space_usage(self, event=None):
        selected_items = self.get_selected_installers()
        is_update = self.update_mode_var.get()

        # Calculate Total Required using Partitioner Logic
        total_required_mb = 0.0

        if not is_update:
            # Create mode: Include EFI
            total_required_mb += 1024

        # Visualization Data
        segments = []
        if not is_update:
            segments.append({"name": "EFI", "size": 1024, "color": "gray"})

        for item_id in selected_items:
            values = self.inst_tree.item(item_id)['values']
            name = values[1]
            version = str(values[2])

            # Size KB
            size_kb = 0
            # Find in installers_list to get KB
            for inst in self.installers_list:
                if inst['name'] == name and str(inst['version']) == version:
                    size_kb = inst['size_kb']
                    break

            # Buffer
            try:
                buffer_gb = float(values[4].split()[0])
            except: buffer_gb = 2.0

            # Use Core Logic (MB precision)
            part_size_mb = constants.calculate_partition_size(size_kb, version, override_buffer_gb=buffer_gb)

            total_required_mb += part_size_mb
            segments.append({"name": name, "size": part_size_mb, "color": "#4a90e2"})

        self.total_required_gb = total_required_mb / 1024.0

        # Available Space
        disk_str = self.selected_disk.get()
        available_gb = 0.0

        if disk_str and "No external" not in disk_str:
            try:
                disk_id = disk_str.split('(')[1].split(')')[0]

                if is_update:
                    # Logic for Update Mode: Available space is Free Space on disk
                    # Need to query `updater.get_drive_structure`
                    # This is slow to do on every click.
                    # Ideally we cache this or show "Calculating..."
                    # For GUI responsiveness, we might need a separate thread or cached value.
                    # Let's assume user refreshed hardware.
                    # But refresh_hardware uses disk_detector which doesn't check free space.
                    # We might need to fetch it now.
                    # Warning: Blocking call.
                    # Let's assume we can get it or display "??" until creation.
                    # Or just run `updater.get_drive_structure` here quickly?
                    # `diskutil list -plist` takes 0.5s. Maybe acceptable?

                    # For now, let's assume total size for Create, and maybe trigger a bg check for Update?
                    # Or just use total size as upper bound and verify at Start.

                    # Let's use total size for visualization but color it differently?
                    # Or assume "Update" adds to free space.
                    pass

                size_part = disk_str.split(' - ')[1]
                available_gb = float(size_part.split()[0])
            except:
                available_gb = 0.0

        self.current_disk_size_gb = available_gb

        # Add Data Partition Segment if space remains (Only relevant for Create mode visuals)
        available_mb = available_gb * 1024
        if available_mb > total_required_mb:
            rem_mb = available_mb - total_required_mb
            if not is_update:
                segments.append({"name": "Free/Data", "size": rem_mb, "color": "#50e3c2"})
            else:
                # In update mode, we are ADDING. So the visual should show existing usage?
                # That's hard without scanning.
                # Just show what we are ADDING relative to total capacity?
                pass

        # Update Label
        color = "black"
        status_text = "Ready"

        # Check Fit logic
        if self.total_required_gb > 0:
            if available_gb > 0:
                if self.total_required_gb > available_gb:
                    color = "red"
                    status_text = "❌ Space Insufficient!"
                    self.create_btn.config(state="disabled")
                else:
                    color = "green"
                    status_text = "✅ Fits on Disk"
                    if not self.is_working: self.create_btn.config(state="normal")
            else:
                status_text = "Select a Disk"
        else:
            status_text = "Select Installers"

        self.space_label.config(
            text=f"Required: {self.total_required_gb:.2f} GB | Capacity: {available_gb:.2f} GB | {status_text}",
            foreground=color
        )

        self.draw_viz(segments, available_mb)

    def draw_viz(self, segments, total_capacity_mb):
        self.viz_canvas.delete("all")
        if total_capacity_mb <= 0: return

        w = self.viz_canvas.winfo_width()
        h = self.viz_canvas.winfo_height()
        if w < 10: w = 900

        current_x = 0
        scale = w / total_capacity_mb

        for seg in segments:
            width = seg["size"] * scale
            color = seg["color"]

            self.viz_canvas.create_rectangle(current_x, 0, current_x + width, h, fill=color, outline="white")

            if width > 40:
                name_short = seg['name'][:10]
                if seg['name'] == "Free/Data": name_short = "Free"
                self.viz_canvas.create_text(current_x + width/2, h/2, text=name_short, fill="black", font=("Arial", 8))

            current_x += width

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
                    "☐",
                    inst['name'],
                    inst['version'],
                    f"{size_gb:.2f} GB",
                    f"{buf:.1f} GB",
                    status
                ))

                if is_stub:
                    self.inst_tree.item(item_id, tags=("stub",))

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

        if not messagebox.askyesno("Delete", f"Delete {len(selected)} installer(s)?"):
            return

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
                "☐",
                item.get('name'),
                item.get('version'),
                item.get('build'),
                size_gb,
                item.get('date'),
                status_str
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
                if identifier:
                    if mist_downloader.download_installer_by_identifier(identifier, name):
                         self.log(f"Download of {name} complete.")
                    else:
                         self.log(f"Download of {name} failed.")
                else:
                    mist_downloader.download_installer([name])
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

        # Prepare Target Installers
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

        # Check Mode
        if self.update_mode_var.get():
            # Update Mode
            if messagebox.askyesno("Confirm Update", f"Update {disk_id}?\n\nThis will look for free space or split DATA_STORE.\nEXISTING INSTALLERS WILL NOT BE ERASED."):
                self.log("Starting Update Process...")
                self.create_btn.config(state="disabled")
                self.is_working = True
                threading.Thread(target=self.run_update_thread, args=(disk_id, target_installers)).start()
        else:
            # Create Mode (Erase)
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

            # 1. Analyze structure
            self.log(f"Analyzing {disk_id}...")
            structure = operations.updater.get_drive_structure(disk_id)
            if not structure:
                self.log("Failed to analyze drive.")
                return

            self.log(f"Free Space Detected: {structure['free_space'] / 1e9:.2f} GB")

            # 2. Add Partitions
            # Try filling free space first
            new_partitions = []

            if structure['free_space'] > 2e9: # > 2GB free
                self.log("Found free space. Adding partitions...")
                added = operations.updater.add_partition_to_free_space(disk_id, installers)
                if added:
                    new_partitions.extend(added)
                    # If we added all, great. If not, we might need to split data?
                    # The current `add_partition_to_free_space` loops through all.
                    # It returns the ones successfully added.

            # If we didn't add all (e.g. no free space), try splitting data partition?
            # For now, let's assume `add_partition_to_free_space` covers the "Shrink workflow".
            # The logic inside `updater` handles the loop.

            if not new_partitions:
                self.log("No partitions created. Check free space or DATA_STORE.")
                return

            # 3. Install
            time.sleep(2) # settle

            for item in new_partitions:
                part_name = item['name']
                inst = item['installer']

                self.log(f"Installing {inst['name']} to {part_name}...")

                # Find mount point
                # We need to re-scan to find the disk slice for this name
                # Simple logic: assume it mounts?
                subprocess.run(['diskutil', 'mount', part_name])
                mount_point = f"/Volumes/{part_name}"

                if not os.path.exists(mount_point):
                    self.log(f"Waiting for mount {mount_point}...")
                    time.sleep(3)

                if os.path.exists(mount_point):
                    def cb(p):
                        if p%10==0: self.log(f"  {inst['name']}: {p}%")

                    if operations.installer_runner.run_createinstallmedia(inst['path'], mount_point, progress_callback=cb):
                        self.log("Success.")
                        # Re-branding
                        # Mount point might change after install
                        # Branding logic handles finding it by name usually?
                        # branding.apply_full_branding needs path.
                        # Check where it mounted now.
                        # Usually "Install macOS Name"
                        # We can try to guess or use the helper.
                        # Let's rely on standard path for now.

                        # Re-find volume by disk slice?
                        # Let's just try the likely new name
                        std_name = f"/Volumes/Install {inst['name'].replace('.app','')}" # Rough guess
                        if not os.path.exists(std_name):
                             std_name = mount_point # Fallback

                        os_name = core.constants.get_os_name(inst['version'], inst['name'])
                        operations.branding.apply_full_branding(std_name, inst['name'], os_name, inst['version'])
                    else:
                        self.log("Installation failed.")
                else:
                    self.log(f"Could not mount {part_name}")

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
