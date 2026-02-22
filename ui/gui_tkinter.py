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
        self.root.geometry("950x700")

        # Variables
        self.selected_disk = tk.StringVar()
        self.installers_list = []
        self.log_queue = queue.Queue()
        self.is_working = False

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

        # Middle: Installer Selection
        inst_frame = ttk.LabelFrame(top_frame, text="2. Select macOS Installers")
        inst_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Treeview for installers
        cols = ("Name", "Version", "Size", "Status")
        self.inst_tree = ttk.Treeview(inst_frame, columns=cols, show="headings", selectmode="extended", height=10)
        for col in cols:
            self.inst_tree.heading(col, text=col)
        self.inst_tree.column("Name", width=250)
        self.inst_tree.column("Version", width=100)
        self.inst_tree.column("Size", width=100)
        self.inst_tree.column("Status", width=100)
        self.inst_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Scrollbar for tree
        scrollbar = ttk.Scrollbar(inst_frame, orient="vertical", command=self.inst_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.inst_tree.configure(yscrollcommand=scrollbar.set)

        # Context Menu for Installers
        self.context_menu = tk.Menu(self.inst_tree, tearoff=0)
        self.context_menu.add_command(label="Delete Installer", command=self.delete_selected_installer)
        self.inst_tree.bind("<Button-3>", self.show_context_menu)

        # Buttons for installers
        btn_frame = ttk.Frame(inst_frame)
        btn_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        ttk.Button(btn_frame, text="Select All", command=self.select_all_installers).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Clear Selection", command=self.deselect_all_installers).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Download New...", command=self.open_download_dialog).pack(side="right", padx=2)

        # Bottom Section: Actions & Log
        bottom_frame = ttk.Frame(paned)
        paned.add(bottom_frame, weight=1)

        # Settings Frame (Buffer, etc.)
        settings_frame = ttk.LabelFrame(bottom_frame, text="3. Settings")
        settings_frame.pack(fill="x", padx=5, pady=5)

        # Buffer Slider
        ttk.Label(settings_frame, text="Safety Buffer (GB):").pack(side="left", padx=5)
        self.buffer_var = tk.DoubleVar(value=2.0)
        self.buffer_scale = ttk.Scale(settings_frame, from_=0.5, to=10.0, variable=self.buffer_var, orient="horizontal")
        self.buffer_scale.pack(side="left", fill="x", expand=True, padx=5)
        self.buffer_label = ttk.Label(settings_frame, text="2.0 GB")
        self.buffer_label.pack(side="left", padx=5)
        self.buffer_scale.configure(command=lambda v: self.buffer_label.configure(text=f"{float(v):.1f} GB"))

        # Action Button
        self.create_btn = ttk.Button(bottom_frame, text="CREATE BOOTABLE USB", command=self.start_creation)
        self.create_btn.pack(fill="x", padx=20, pady=10)

        # Log Output
        log_frame = ttk.LabelFrame(bottom_frame, text="Progress Log")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, state="disabled", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

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

    def refresh_hardware(self):
        self.log("Scanning hardware...")
        # Scan Disks
        try:
            drives = disk_detector.get_external_usb_drives()
            options = []
            if drives:
                for d in drives:
                    options.append(f"{d['name']} ({d['id']}) - {d['size_gb']:.1f} GB")
                self.disk_combo['values'] = options
                if options:
                    self.disk_combo.current(0)
                self.log(f"Found {len(drives)} USB drive(s).")
            else:
                self.disk_combo['values'] = ["No external USB drives found"]
                self.disk_combo.set("No external USB drives found")
                self.log("No USB drives found.")
        except Exception as e:
            self.log(f"Error scanning drives: {e}")

        # Scan Installers
        self.scan_installers()

    def scan_installers(self):
        # Clear tree
        for item in self.inst_tree.get_children():
            self.inst_tree.delete(item)

        self.installers_list = installer_scanner.scan_for_installers()

        # Apply stub check properly
        import detection.stub_validator

        if self.installers_list:
            for inst in self.installers_list:
                is_stub = detection.stub_validator.is_stub_installer(inst['path'])
                inst['is_stub'] = is_stub
                status = "STUB" if is_stub else inst.get('status', 'FULL')

                size_gb = inst['size_kb'] / (1024 * 1024)

                # Insert into tree
                item_id = self.inst_tree.insert("", "end", values=(
                    inst['name'],
                    inst['version'],
                    f"{size_gb:.2f} GB",
                    status
                ))

                # Tag Stubs for visual
                if is_stub:
                    self.inst_tree.item(item_id, tags=("stub",))

            self.inst_tree.tag_configure("stub", foreground="gray")
            self.log(f"Found {len(self.installers_list)} local installer(s).")
        else:
            self.log("No local installers found.")

    def select_all_installers(self):
        for item in self.inst_tree.get_children():
            # Don't select stubs
            tags = self.inst_tree.item(item, "tags")
            if "stub" not in tags:
                self.inst_tree.selection_add(item)

    def deselect_all_installers(self):
        for item in self.inst_tree.get_children():
            self.inst_tree.selection_remove(item)

    def show_context_menu(self, event):
        item = self.inst_tree.identify_row(event.y)
        if item:
            self.inst_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def delete_selected_installer(self):
        selected = self.inst_tree.selection()
        if not selected: return

        item = selected[0]
        values = self.inst_tree.item(item)['values']
        name = values[0]

        # Find path
        path = None
        for inst in self.installers_list:
            if inst['name'] == name:
                path = inst['path']
                break

        if path and messagebox.askyesno("Delete Installer", f"Are you sure you want to delete:\n{path}\n\nThis cannot be undone."):
            try:
                subprocess.run(['sudo', 'rm', '-rf', path], check=True)
                self.log(f"Deleted {name}")
                self.scan_installers()
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to delete: {e}")

    def open_download_dialog(self):
        # Ask for search term
        search = simpledialog.askstring("Download Installer", "Enter search term (e.g. 'Sonoma', '13.6', '12') [Empty for All]:")
        # Allow empty to show list? simpledialog returns '' if OK pressed with empty.

        self.log(f"Searching Mist for '{search}'...")
        threading.Thread(target=self.run_mist_search, args=(search,)).start()

    def run_mist_search(self, search_term):
        self.create_btn.config(state="disabled")
        try:
             # Check mist
            if not mist_downloader.check_mist_available():
                self.log("Mist-CLI missing. Attempting install...")
                mist_downloader.install_mist()

            # Use new structured list function
            installers = mist_downloader.list_installers(search_term)

            if not installers:
                self.log("No installers found matching that term.")
                return

            # Show results in a new dialog window
            self.root.after(0, lambda: self.show_download_selection(installers))

        except Exception as e:
            self.log(f"Error searching: {e}")
        finally:
            self.root.after(0, lambda: self.create_btn.config(state="normal"))

    def show_download_selection(self, data):
        # Create a TopLevel window
        top = tk.Toplevel(self.root)
        top.title("Select Version to Download")
        top.geometry("800x500")

        cols = ("Name", "Version", "Build", "Size", "Date", "Status")
        tree = ttk.Treeview(top, columns=cols, show="headings", selectmode="extended")

        for c in cols:
            tree.heading(c, text=c)
            if c == "Name":
                tree.column(c, width=200)
            else:
                tree.column(c, width=100)

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Insert data
        for item in data:
            size_bytes = item.get('size', 0)
            size_gb = f"{size_bytes / (1024**3):.1f} GB"

            status_flags = []
            if item.get('downloaded'): status_flags.append("Installed")
            if item.get('latest'): status_flags.append("Latest")
            status_str = ", ".join(status_flags)

            item_id = tree.insert("", "end", values=(
                item.get('name'),
                item.get('version'),
                item.get('build'),
                size_gb,
                item.get('date'),
                status_str
            ))

            # Highlighting
            if item.get('latest'):
                tree.item(item_id, tags=("latest",))
            if item.get('downloaded'):
                tree.item(item_id, tags=("installed",))

        tree.tag_configure("latest", font=("TkDefaultFont", 10, "bold"))
        tree.tag_configure("installed", foreground="gray")

        def do_download():
            sel = tree.selection()
            if not sel: return

            selected_items = []
            for s in sel:
                # Get raw data mapping logic?
                # Tree view values are strings.
                # Ideally we want the identifier which isn't shown but is in data.
                # We can store identifier in tags or lookup.
                # Simple lookup by values since Name+Version+Build is unique enough.

                vals = tree.item(s)['values']
                name = vals[0]
                version = str(vals[1])
                build = str(vals[2])

                # Find matching identifier in original data
                identifier = None
                for d in data:
                    if d.get('name') == name and d.get('version') == version and d.get('build') == build:
                        identifier = d.get('identifier')
                        break

                if identifier:
                    selected_items.append((identifier, name))
                else:
                    selected_items.append((None, name)) # Fallback

            top.destroy()

            # Start download thread
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
                    # Fallback
                    if mist_downloader.download_installer([name]):
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
        if "No external" in disk_str or not disk_str:
            messagebox.showwarning("Warning", "No disk selected.")
            return

        disk_id = disk_str.split('(')[1].split(')')[0]

        if messagebox.askyesno("Format Disk", f"WARNING: This will completely ERASE {disk_id} and format it as MacOS Extended (Journaled).\n\nAre you sure?"):
             threading.Thread(target=self.run_format_disk, args=(disk_id,)).start()

    def run_format_disk(self, disk_id):
        self.log(f"Formatting {disk_id}...")
        try:
            cmd = ['diskutil', 'eraseDisk', 'JHFS+', 'UNTITLED', disk_id]
            subprocess.run(cmd, check=True)
            self.log(f"Format complete: {disk_id}")
            self.root.after(0, lambda: messagebox.showinfo("Success", "Disk Formatted Successfully"))
            self.root.after(0, self.refresh_hardware)
        except Exception as e:
            self.log(f"Format failed: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Format failed: {e}"))

    def start_creation(self):
        selected_items = self.inst_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select at least one installer.")
            return

        disk_str = self.selected_disk.get()
        if "No external" in disk_str or not disk_str:
            messagebox.showwarning("Warning", "Please select a target disk.")
            return

        try:
            disk_id = disk_str.split('(')[1].split(')')[0]
        except IndexError:
            self.log("Error parsing disk ID.")
            return

        # Check Stubs
        target_installers = []
        for item_id in selected_items:
            tags = self.inst_tree.item(item_id, "tags")
            values = self.inst_tree.item(item_id)['values']
            name = values[0]

            if "stub" in tags:
                messagebox.showerror("Error", f"Cannot use '{name}' because it is a STUB installer.\nPlease download a full version.")
                return

            # Match to object
            version = str(values[1])
            found = False
            for inst in self.installers_list:
                if inst['name'] == name and str(inst['version']) == version:
                    target_installers.append(inst)
                    found = True
                    break
            if not found:
                self.log(f"Warning: Could not match {name} to source object.")

        if not target_installers: return

        if messagebox.askyesno("Confirm", f"This will ERASE {disk_id}.\n\nInstallers: {len(target_installers)}\nSafety Buffer: {self.buffer_var.get()} GB\n\nALL DATA WILL BE LOST. Continue?"):
            self.log("Starting creation process...")
            self.create_btn.config(state="disabled")

            # Start thread
            threading.Thread(target=self.run_creation_thread, args=(disk_id, target_installers)).start()

    def run_creation_thread(self, disk_id, installers):
        try:
            # 1. Backup
            self.log("Backing up partition table...")
            import safety.backup_manager
            backup = safety.backup_manager.backup_partition_table(disk_id)
            if backup: self.log(f"Backup saved to {backup}")

            # 2. Extract Icons
            self.log("Extracting icons...")
            for inst in installers:
                branding.extract_icon_from_installer(inst['path'], inst['name'])

            # 3. Partitioning
            # Update buffer constant dynamically?
            # Ideally core constants should be configurable.
            # Hack: modify global for this run
            constants.OS_DATABASE["default_buffer"] = self.buffer_var.get()

            import operations.updater
            struct = operations.updater.get_drive_structure(disk_id)
            if not struct:
                self.log("Failed to get disk info.")
                return

            total_size_gb = struct['disk_size'] / 1e9

            self.log(f"Partitioning {disk_id} ({total_size_gb:.1f} GB)...")
            success = partitioner.create_multiboot_layout(disk_id, installers, total_size_gb)
            if not success:
                self.log("Partitioning failed!")
                return

            self.log("Partitioning successful. Waiting for volumes to mount...")
            time.sleep(5)

            # 4. Installation
            current_partitions = partitioner.get_partition_list(disk_id)

            for inst in installers:
                self.log(f"Preparing to install {inst['name']}...")

                # Find partition by name logic used in partitioner
                os_name = constants.get_os_name(inst['version'])
                version_clean = inst['version'].replace('.', '_').split()[0]
                expected_vol_name = f"INSTALL_{os_name}_{version_clean}"[:27]

                # Find matching partition
                target_part = next((p for p in current_partitions if p['name'] == expected_vol_name), None)

                if not target_part:
                    # Retry scan
                    time.sleep(2)
                    current_partitions = partitioner.get_partition_list(disk_id)
                    target_part = next((p for p in current_partitions if p['name'] == expected_vol_name), None)

                if not target_part:
                    self.log(f"Could not find partition for {inst['name']}")
                    continue

                # Get mount point
                part_id = target_part['id']
                # extract partition number
                part_num = part_id.replace(disk_id, '').replace('s', '')

                mount_point = installer_runner.get_volume_mount_point(disk_id, part_num)
                if not mount_point:
                    self.log(f"Mounting {part_id}...")
                    subprocess.run(['diskutil', 'mount', part_id])
                    time.sleep(1)
                    mount_point = installer_runner.get_volume_mount_point(disk_id, part_num)

                if not mount_point:
                    self.log(f"Failed to mount {part_id}")
                    continue

                # Run createinstallmedia
                def progress_cb(pct):
                    if pct % 5 == 0:
                        self.log(f"  {inst['name']}: {pct}%")

                self.log(f"Running createinstallmedia for {inst['name']}...")
                success = installer_runner.run_createinstallmedia(
                    inst['path'], mount_point, progress_callback=progress_cb
                )

                if success:
                    self.log(f"Installation of {inst['name']} complete.")
                    # Branding
                    # Re-fetch mount point
                    new_mount = installer_runner.get_volume_mount_point(disk_id, part_num)
                    if new_mount:
                        branding.apply_full_branding(new_mount, inst['name'], os_name, inst['version'])
                        self.log("Branding applied.")
                else:
                    self.log(f"Installation of {inst['name']} failed.")

            self.log("All operations complete.")
            self.root.after(0, lambda: messagebox.showinfo("Success", "Multi-Boot USB Created Successfully!"))

        except Exception as e:
            self.log(f"Critical Error: {e}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.root.after(0, lambda: self.create_btn.config(state="normal"))

def launch(config=None):
    if os.geteuid() != 0:
        print("Warning: Running GUI without root. Operations may fail.")

    root = tk.Tk()
    app = MultiBootGUI(root, config)
    root.mainloop()

if __name__ == "__main__":
    launch()
