import tkinter as tk
from tkinter import ttk

class InstallerTree(ttk.LabelFrame):
    def __init__(self, parent, on_click, on_double_click, on_right_click, apply_filter_command):
        super().__init__(parent, text="2. Select macOS Installers (To Add/Update)")
        self.on_click = on_click
        self.on_double_click = on_double_click
        self.on_right_click = on_right_click
        self.apply_filter_command = apply_filter_command

        self.filter_var = tk.StringVar(value="all")
        self.search_var = tk.StringVar()

        self.create_widgets()

    def create_widgets(self):
        # Filter Bar
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill="x", padx=5, pady=2)

        ttk.Label(filter_frame, text="Show:").pack(side="left", padx=2)
        ttk.Radiobutton(filter_frame, text="All", variable=self.filter_var, value="all", command=self.apply_filter_command).pack(side="left", padx=2)
        ttk.Radiobutton(filter_frame, text="Local Only", variable=self.filter_var, value="local", command=self.apply_filter_command).pack(side="left", padx=2)
        ttk.Radiobutton(filter_frame, text="Remote Only", variable=self.filter_var, value="remote", command=self.apply_filter_command).pack(side="left", padx=2)

        ttk.Label(filter_frame, text="Search:").pack(side="left", padx=(20, 2))
        self.search_var.trace("w", lambda *args: self.apply_filter_command())
        ttk.Entry(filter_frame, textvariable=self.search_var, width=20).pack(side="left", padx=2)

        # Tree
        cols = ("Select", "Name", "Version", "Build", "Size", "Buffer", "Source", "Status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="extended", height=10)

        self.tree.heading("Select", text="[x]")
        self.tree.column("Select", width=50, anchor="center")
        self.tree.heading("Name", text="Name")
        self.tree.column("Name", width=220)
        self.tree.heading("Version", text="Version")
        self.tree.column("Version", width=70)
        self.tree.heading("Build", text="Build")
        self.tree.column("Build", width=60)
        self.tree.heading("Size", text="Size")
        self.tree.column("Size", width=70)
        self.tree.heading("Buffer", text="Buffer")
        self.tree.column("Buffer", width=60)
        self.tree.heading("Source", text="Source")
        self.tree.column("Source", width=60, anchor="center")
        self.tree.heading("Status", text="Status")
        self.tree.column("Status", width=100)

        self.tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Bindings
        self.tree.bind("<Button-1>", self.on_click)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        self.select_all_btn = ttk.Button(btn_frame, text="Select All")
        self.select_all_btn.pack(side="left", padx=2)
        self.unselect_all_btn = ttk.Button(btn_frame, text="Unselect All")
        self.unselect_all_btn.pack(side="left", padx=2)
        self.delete_local_btn = ttk.Button(btn_frame, text="Delete Local")
        self.delete_local_btn.pack(side="left", padx=20)
        self.refresh_btn = ttk.Button(btn_frame, text="Refresh List")
        self.refresh_btn.pack(side="right", padx=2)
