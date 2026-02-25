import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add repo root to path
sys.path.append(os.getcwd())

# Define dummy base classes for tkinter widgets
class MockTk:
    def __init__(self, *args, **kwargs):
        self.tk = MagicMock()
    def title(self, val): pass
    def geometry(self, val): pass
    def resizable(self, w, h): pass
    def mainloop(self): pass
    def quit(self): pass
    def destroy(self): pass
    def call(self, *args): pass
    def winfo_screenwidth(self): return 1920
    def winfo_screenheight(self): return 1080
    def update_idletasks(self): pass
    def protocol(self, name, func): pass
    def winfo_width(self): return 1000
    def winfo_height(self): return 800
    def bind(self, event, func): pass
    def config(self, **kwargs): pass
    def after(self, ms, func=None):
        # Do not run immediately to avoid recursion in loops
        return "after_id"
    def option_add(self, *args): pass

class MockWidget:
    def __init__(self, master=None, **kwargs): pass
    def pack(self, **kwargs): pass
    def pack_forget(self): pass
    def grid(self, **kwargs): pass
    def bind(self, event, func): pass
    def config(self, **kwargs): pass
    def configure(self, **kwargs): pass
    def destroy(self): pass
    def focus(self): pass
    def update(self): pass
    def winfo_width(self): return 100
    def winfo_height(self): return 100
    def cget(self, key): return "100"
    def set(self, *args): pass
    def after(self, ms, func=None, *args):
        if func: func(*args)
        return "after_id"

class MockLabelFrame(MockWidget): pass
class MockFrame(MockWidget): pass
class MockScale(MockWidget): pass
class MockPanedWindow(MockWidget):
    def add(self, widget, **kwargs): pass
class MockNotebook(MockWidget):
    def add(self, widget, **kwargs): pass
    def select(self, tab_id=None): return "tab_id"

class MockCombobox(MockWidget):
    def current(self, new_index=None): return 0
    def set(self, value): pass
    def get(self): return ""
    def __setitem__(self, key, value): pass
    def __getitem__(self, key): return []

class MockCanvas(MockWidget):
    def __init__(self, master=None, **kwargs): pass
    def create_rectangle(self, *args, **kwargs): pass
    def create_text(self, *args, **kwargs): pass
    def delete(self, tag): pass
    def bind(self, event, func): pass
    def canvasx(self, x): return x
    def canvasy(self, y): return y
    def find_closest(self, x, y): return (1,)
    def gettags(self, item): return ("seg_0",)

class MockTreeview(MockWidget):
    def heading(self, col, **kwargs): pass
    def column(self, col, **kwargs): pass
    def insert(self, parent, index, **kwargs): return "item_id"
    def delete(self, item): pass
    def get_children(self, item=None): return []
    def item(self, item, **kwargs): return {'values': [], 'tags': []}
    def selection(self): return []
    def selection_set(self, item): pass
    def see(self, item): pass
    def set(self, item, col, value=None): return "value"
    def tag_configure(self, tag, **kwargs): pass
    def identify(self, region, x, y): return "region"
    def identify_column(self, x): return "#1"
    def identify_row(self, y): return "item_id"
    def focus(self, item=None): pass
    def yview(self, *args): pass

class MockMenu:
    def __init__(self, master=None, **kwargs): pass
    def add_cascade(self, **kwargs): pass
    def add_command(self, **kwargs): pass
    def add_separator(self, **kwargs): pass
    def post(self, x, y): pass

# Create mock module for tkinter
mock_tk = MagicMock()
mock_tk.Tk = MockTk
mock_tk.StringVar = MagicMock
mock_tk.BooleanVar = MagicMock
mock_tk.IntVar = MagicMock
mock_tk.DoubleVar = MagicMock
mock_tk.Canvas = MockCanvas
mock_tk.Menu = MockMenu
mock_tk.Toplevel = MockWidget # Behave like widget
mock_tk.Text = MockWidget

# Create mock module for tkinter.ttk
mock_ttk = MagicMock()
mock_ttk.LabelFrame = MockLabelFrame
mock_ttk.Frame = MockFrame
mock_ttk.Label = MockWidget
mock_ttk.Button = MockWidget
mock_ttk.Checkbutton = MockWidget
mock_ttk.Combobox = MockCombobox
mock_ttk.Treeview = MockTreeview
mock_ttk.Scrollbar = MockWidget
mock_ttk.Progressbar = MockWidget
mock_ttk.Notebook = MockNotebook
mock_ttk.Scale = MockScale
mock_ttk.PanedWindow = MockPanedWindow

# Link ttk to tk
mock_tk.ttk = mock_ttk

sys.modules['tkinter'] = mock_tk
sys.modules['tkinter.ttk'] = mock_ttk
sys.modules['tkinter.messagebox'] = MagicMock()
sys.modules['tkinter.filedialog'] = MagicMock()
sys.modules['tkinter.scrolledtext'] = MagicMock()
sys.modules['tkinter.simpledialog'] = MagicMock()

# Mock external dependencies
sys.modules['requests'] = MagicMock()
sys.modules['ui.display'] = MagicMock()
sys.modules['utils.logger'] = MagicMock()

# Import the GUI
from ui.gui_tkinter import MultiBootGUI

class TestGUIIntegration(unittest.TestCase):

    @patch('ui.gui_tkinter.mist_downloader')
    @patch('ui.gui_tkinter.disk_detector')
    @patch('ui.gui_tkinter.installer_scanner')
    @patch('ui.gui_tkinter.config_manager')
    def test_gui_initialization(self, mock_config_manager, mock_scanner, mock_disk_detector, mock_mist):
        # Mock responses
        mock_disk_detector.get_external_usb_drives.return_value = []
        mock_mist.list_installers.return_value = []
        mock_scanner.scan_for_installers.return_value = []
        mock_config_manager.load_config.return_value = {}

        # Instantiate GUI
        root = MockTk()
        app = MultiBootGUI(root)

        # Check if components were initialized
        self.assertTrue(hasattr(app, 'disk_selector'), "DiskSelector missing")
        self.assertTrue(hasattr(app, 'installer_tree_frame'), "InstallerTree missing")
        self.assertTrue(hasattr(app, 'status_panel'), "StatusPanel missing")
        self.assertTrue(hasattr(app, 'action_panel'), "ActionPanel missing")
        self.assertTrue(hasattr(app, 'viz_canvas'), "VisualizationCanvas missing")

        print("GUI Integration Test Passed: All components instantiated correctly.")

if __name__ == '__main__':
    unittest.main()
