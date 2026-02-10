"""
test_imports.py - Verify all modules can be imported
"""

import sys
import os
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestImports(unittest.TestCase):
    def test_core_imports(self):
        from core import constants, privilege
        self.assertIsNotNone(constants)
        self.assertIsNotNone(privilege)

    def test_detection_imports(self):
        from detection import installer_scanner, stub_validator, disk_detector, version_parser
        self.assertIsNotNone(installer_scanner)
        self.assertIsNotNone(stub_validator)
        self.assertIsNotNone(disk_detector)
        self.assertIsNotNone(version_parser)

    def test_safety_imports(self):
        from safety import boot_disk_guard, backup_manager
        self.assertIsNotNone(boot_disk_guard)
        self.assertIsNotNone(backup_manager)

    def test_operations_imports(self):
        from operations import partitioner, installer_runner, branding
        self.assertIsNotNone(partitioner)
        self.assertIsNotNone(installer_runner)
        self.assertIsNotNone(branding)

    def test_integration_imports(self):
        from integration import mist_downloader
        self.assertIsNotNone(mist_downloader)

    def test_ui_imports(self):
        from ui import display, prompts, progress
        self.assertIsNotNone(display)
        self.assertIsNotNone(prompts)
        self.assertIsNotNone(progress)

    def test_utils_imports(self):
        from utils import logger
        self.assertIsNotNone(logger)

if __name__ == '__main__':
    unittest.main()
