import tkinter as tk
from tkinter import ttk
from detection import disk_detector

class DiskSelector(ttk.LabelFrame):
    def __init__(self, parent, on_disk_selected, show_all_var, refresh_command):
        super().__init__(parent, text="1. Select Target USB Drive")
        self.on_disk_selected = on_disk_selected
        self.show_all_var = show_all_var
        self.refresh_command = refresh_command
        self.selected_disk = tk.StringVar()

        self.create_widgets()

    def create_widgets(self):
        # Combo
        self.disk_combo = ttk.Combobox(self, textvariable=self.selected_disk, state="readonly", width=60)
        self.disk_combo.pack(fill="x", padx=10, pady=10)
        self.disk_combo.bind("<<ComboboxSelected>>", self.on_select)

        # Options
        opt_frame = ttk.Frame(self)
        opt_frame.pack(fill="x", padx=10, pady=5)

        ttk.Checkbutton(opt_frame, text="Show All Disks (Advanced)",
                        variable=self.show_all_var,
                        command=self.refresh_command).pack(side="left")

        # Mode Label Placeholder (Managed by parent or ModeManager)
        self.mode_label = ttk.Label(opt_frame, text="Mode: Select Disk", font=("Arial", 10, "bold"))
        self.mode_label.pack(side="left", padx=(20, 5))
        self.change_mode_btn = ttk.Button(opt_frame, text="Change...", width=8)
        self.change_mode_btn.pack(side="left", padx=5)

    def on_select(self, event):
        if self.on_disk_selected:
            self.on_disk_selected(event)

    def update_disks(self):
        # Set loading state
        self.disk_combo.set("Scanning for drives...")
        self.disk_combo['values'] = ["Scanning..."]
        self.disk_combo.config(state="disabled")

        import threading
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        try:
            show_all = self.show_all_var.get()
            # This is the blocking call
            drives = disk_detector.get_external_usb_drives(show_all=show_all)
            # Schedule UI update on main thread
            self.after(0, self._update_ui, drives)
        except Exception as e:
            print(f"Error scanning drives: {e}")
            self.after(0, self._update_ui, [])

    def _update_ui(self, drives):
        try:
            self.disk_combo.config(state="readonly")
            options = []
            if drives:
                for d in drives:
                    # Enhanced Details: Name (ID) - Size - Protocol - Type
                    proto = d.get('protocol', 'USB')
                    media = d.get('media_type', '')
                    details = f"[{proto}"
                    if media: details += f"/{media}"
                    details += "]"

                    options.append(f"{d['name']} ({d['id']}) - {d['size_gb']:.1f} GB {details}")
                self.disk_combo['values'] = options
                if options: self.disk_combo.current(0)
                self.on_select(None)
            else:
                self.disk_combo['values'] = ["No external USB drives found"]
                self.disk_combo.set("No external USB drives found")
                # Ensure we trigger on_select to clear dependent UI if needed
                self.on_select(None)
        except Exception as e:
            print(f"Error updating UI: {e}")

    def get_selected_id(self):
        val = self.selected_disk.get()
        if not val or "No external" in val: return None
        try:
            # Parse "Name (disk2) - ..."
            return val.split('(')[1].split(')')[0]
        except: return None
