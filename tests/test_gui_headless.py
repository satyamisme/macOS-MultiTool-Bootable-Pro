"""
test_gui_headless.py - Verify GUI imports and class structure without a display
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestGUIHeadless(unittest.TestCase):

    @patch('tkinter.Tk')
    def test_gui_class_initialization(self, mock_tk):
        """Test that MultiBootGUI class can be instantiated with a mocked root."""
        # Mock Tkinter variables
        mock_root = MagicMock()

        # We need to mock other tkinter modules used in gui_tkinter
        with patch('tkinter.ttk.Combobox'), \
             patch('tkinter.ttk.Treeview'), \
             patch('tkinter.scrolledtext.ScrolledText'), \
             patch('tkinter.StringVar'), \
             patch('ui.gui_tkinter.disk_detector.get_external_usb_drives', return_value=[]), \
             patch('ui.gui_tkinter.installer_scanner.scan_for_installers', return_value=[]):

            from ui import gui_tkinter

            # Instantiate
            gui = gui_tkinter.MultiBootGUI(mock_root)

            # Check basic attributes
            self.assertIsNotNone(gui.root)
            self.assertEqual(gui.installers_list, [])

if __name__ == '__main__':
    unittest.main()
