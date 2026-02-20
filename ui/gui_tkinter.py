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
import subprocess
import time

# Import core modules
from detection import installer_scanner, disk_detector
from core import privilege, constants
from operations import partitioner, installer_runner, branding
from integration import mist_downloader

class MultiBootGUI:
    def __init__(self, root, config=None):
        self.root = root
        self.config = config
        self.root.title("macOS Multi-Tool Pro")
        self.root.geometry("800x600")

        # Variables
        self.selected_disk = tk.StringVar()
        self.installers_list = []
        self.selected_installers = []
        self.log_queue = queue.Queue()

        # Layout
        self.create_widgets()

        # Start log poller
        self.poll_log_queue()

        # Initial scan
        self.refresh_hardware()

    def create_widgets(self):
        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(header_frame, text="macOS Multi-Boot Creator", font=("Arial", 18, "bold")).pack(side="left")
        ttk.Button(header_frame, text="Refresh All", command=self.refresh_hardware).pack(side="right")

        # Main PanedWindow
        paned = ttk.PanedWindow(self.root, orient="vertical")
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        # Top Section: Selection
        top_frame = ttk.Frame(paned)
        paned.add(top_frame, weight=1)

        # Left: Disk Selection
        disk_frame = ttk.LabelFrame(top_frame, text="1. Select Target USB Drive")
        disk_frame.pack(fill="x", padx=5, pady=5)

        self.disk_combo = ttk.Combobox(disk_frame, textvariable=self.selected_disk, state="readonly", width=50)
        self.disk_combo.pack(fill="x", padx=10, pady=10)

        # Middle: Installer Selection
        inst_frame = ttk.LabelFrame(top_frame, text="2. Select macOS Installers")
        inst_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Treeview for installers
        cols = ("Name", "Version", "Size", "Status")
        self.inst_tree = ttk.Treeview(inst_frame, columns=cols, show="headings", selectmode="extended", height=8)
        for col in cols:
            self.inst_tree.heading(col, text=col)
            self.inst_tree.column(col, width=100)
        self.inst_tree.column("Name", width=250)
        self.inst_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Scrollbar for tree
        scrollbar = ttk.Scrollbar(inst_frame, orient="vertical", command=self.inst_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.inst_tree.configure(yscrollcommand=scrollbar.set)

        # Buttons for installers
        btn_frame = ttk.Frame(inst_frame)
        btn_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        ttk.Button(btn_frame, text="Select All", command=self.select_all_installers).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Clear Selection", command=self.deselect_all_installers).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Download New...", command=self.open_download_dialog).pack(side="right", padx=2)

        # Bottom Section: Actions & Log
        bottom_frame = ttk.Frame(paned)
        paned.add(bottom_frame, weight=1)

        # Action Button
        self.create_btn = ttk.Button(bottom_frame, text="CREATE BOOTABLE USB", command=self.start_creation)
        self.create_btn.pack(fill="x", padx=20, pady=10)

        # Log Output
        log_frame = ttk.LabelFrame(bottom_frame, text="Progress Log")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state="disabled", font=("Consolas", 10))
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
        drives = disk_detector.get_external_usb_drives()
        options = []
        if drives:
            for d in drives:
                options.append(f"{d['name']} ({d['id']}) - {d['size_gb']:.1f} GB")
            self.disk_combo['values'] = options
            self.disk_combo.current(0)
            self.log(f"Found {len(drives)} USB drive(s).")
        else:
            self.disk_combo['values'] = ["No external USB drives found"]
            self.disk_combo.current(0)
            self.log("No USB drives found.")

        # Scan Installers
        self.scan_installers()

    def scan_installers(self):
        # Clear tree
        for item in self.inst_tree.get_children():
            self.inst_tree.delete(item)

        self.installers_list = installer_scanner.scan_for_installers()

        if self.installers_list:
            for inst in self.installers_list:
                size_gb = inst['size_kb'] / (1024 * 1024)
                status = inst.get('status', 'FULL')

                # Highlight partials? We can use tags but for now just text
                self.inst_tree.insert("", "end", values=(
                    inst['name'],
                    inst['version'],
                    f"{size_gb:.2f} GB",
                    status
                ))
            self.log(f"Found {len(self.installers_list)} local installer(s).")
        else:
            self.log("No local installers found.")

    def select_all_installers(self):
        for item in self.inst_tree.get_children():
            self.inst_tree.selection_add(item)

    def deselect_all_installers(self):
        for item in self.inst_tree.get_children():
            self.inst_tree.selection_remove(item)

    def open_download_dialog(self):
        # Allow multi-download via comma separation
        import tkinter.simpledialog
        search = tkinter.simpledialog.askstring("Download Installer", "Enter macOS Names/Versions (comma-separated):")
        if search:
            targets = [t.strip() for t in search.split(',') if t.strip()]
            self.log(f"Queuing download for: {', '.join(targets)}")
            threading.Thread(target=self.run_download_thread, args=(targets,)).start()

    def run_download_thread(self, targets):
        self.create_btn.config(state="disabled")
        try:
            # Check mist
            if not mist_downloader.check_mist_available():
                self.log("Mist-CLI missing. Attempting install...")
                mist_downloader.install_mist()

            # Download
            self.log(f"Running mist download for: {targets}...")

            if mist_downloader.download_installer(targets):
                self.log("Download complete!")
                self.root.after(0, self.scan_installers)
            else:
                self.log("Download failed. Check logs.")
        except Exception as e:
            self.log(f"Error during download: {e}")
        finally:
            self.root.after(0, lambda: self.create_btn.config(state="normal"))

    def start_creation(self):
        selected_items = self.inst_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select at least one installer.")
            return

        disk_str = self.selected_disk.get()
        if "No external" in disk_str or not disk_str:
            messagebox.showwarning("Warning", "Please select a target disk.")
            return

        # Parse disk ID from string "Name (disk2) - Size"
        try:
            disk_id = disk_str.split('(')[1].split(')')[0]
        except IndexError:
            self.log("Error parsing disk ID.")
            return

        if messagebox.askyesno("Confirm", f"This will ERASE {disk_id}. ALL DATA WILL BE LOST.\nContinue?"):
            self.log("Starting creation process...")
            self.create_btn.config(state="disabled")

            # Match selected items back to installer objects
            target_installers = []
            for item_id in selected_items:
                values = self.inst_tree.item(item_id)['values']
                name = values[0]
                version = str(values[1])

                # Find in local list
                found = False
                for inst in self.installers_list:
                    if inst['name'] == name and str(inst['version']) == version:
                        target_installers.append(inst)
                        found = True
                        break
                if not found:
                    self.log(f"Warning: Could not match {name} to source object.")

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
            # Need total disk size. We can get it from disk_detector or check again.
            # Assuming we can get it from the disk_str logic or querying updater.get_drive_structure
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
            time.sleep(3)

            # 4. Installation
            # We need to find the partitions.
            # Assumption: s2 is custom EFI, s3 is first installer?
            # Or use names.
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
                    # Fallback: try to find by index if names fail?
                    # Or re-scan partitions
                    current_partitions = partitioner.get_partition_list(disk_id)
                    target_part = next((p for p in current_partitions if p['name'] == expected_vol_name), None)

                if not target_part:
                    self.log(f"Could not find partition for {inst['name']}")
                    continue

                # Get mount point
                # installer_runner needs mount point.
                # If partition is unmounted, mount it.
                part_id = target_part['id']
                # extract partition number
                part_num = part_id.replace(disk_id, '').replace('s', '')

                mount_point = installer_runner.get_volume_mount_point(disk_id, part_num)
                if not mount_point:
                    self.log(f"Mounting {part_id}...")
                    subprocess.run(['diskutil', 'mount', part_id])
                    mount_point = installer_runner.get_volume_mount_point(disk_id, part_num)

                if not mount_point:
                    self.log(f"Failed to mount {part_id}")
                    continue

                # Run createinstallmedia
                # We can pass a callback to update log
                def progress_cb(pct):
                    # We could update a progress bar here
                    # For now just log sparingly
                    if pct % 10 == 0:
                        self.log(f"  {inst['name']}: {pct}%")

                self.log(f"Running createinstallmedia for {inst['name']}...")
                success = installer_runner.run_createinstallmedia(
                    inst['path'], mount_point, progress_callback=progress_cb
                )

                if success:
                    self.log(f"Installation of {inst['name']} complete.")
                    # Branding
                    # Re-fetch mount point as name changes
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
        # Warn but allow launch, though operations will fail if sudo not cached
        print("Warning: Running GUI without root. Operations may fail.")

    root = tk.Tk()
    app = MultiBootGUI(root, config)
    root.mainloop()

if __name__ == "__main__":
    launch()
