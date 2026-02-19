"""
test_integration.py - Integration tests with mocked system calls
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import constants
from detection import installer_scanner, disk_detector
from operations import partitioner
import subprocess

class TestIntegration(unittest.TestCase):

    @patch('os.listdir')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    @patch('subprocess.check_output')
    @patch('plistlib.load')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b'plist_data')
    def test_installer_detection_flow(self, mock_file, mock_plist, mock_subprocess, mock_isdir, mock_exists, mock_listdir):
        """Test full flow of detecting valid installers"""

        # Setup mocks
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_listdir.return_value = ["Install macOS Sonoma.app"]

        # Mock plist data
        mock_plist.return_value = {
            "CFBundleShortVersionString": "14.6.1",
            "CFBundleIdentifier": "com.apple.InstallAssistant.Sonoma"
        }

        # Mock size check (du)
        mock_subprocess.return_value = b"14000000\t/Applications/Install macOS Sonoma.app"

        # Run detection
        # Note: installer_scanner.scan_for_installers calls os.path.realpath
        # We need to mock os.path.realpath or adjust expectations if it's not mocked
        with patch('os.path.realpath', side_effect=lambda x: x):
            # We also need to mock os.path.join because it's used inside the loop
            with patch('os.path.join', side_effect=os.path.join):
                installers = installer_scanner.scan_for_installers(["/Applications"])

        # Verify
        self.assertEqual(len(installers), 1)
        self.assertEqual(installers[0]['name'], "Install macOS Sonoma.app")
        self.assertEqual(installers[0]['version'], "14.6.1")
        self.assertGreater(installers[0]['size_kb'], 1000000)

    @patch('subprocess.check_output')
    @patch('subprocess.run')
    def test_partition_command_generation(self, mock_run, mock_check_output):
        """Test partition command construction"""

        disk_id = "disk9"
        installers = [{
            'name': 'Install macOS Sonoma.app',
            'version': '14.6.1',
            'size_kb': 14000000
        }]

        # Mock successful execution
        mock_run.return_value = MagicMock(returncode=0)

        # Run partitioner
        success = partitioner.create_multiboot_layout(disk_id, installers, 64.0)

        self.assertTrue(success)

        # Verify command arguments
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "sudo")
        self.assertEqual(args[1], "diskutil")
        self.assertEqual(args[2], "partitionDisk")
        self.assertIn("/dev/disk9", args)
        self.assertIn("GPT", args)
        # Check for partition triplet
        self.assertIn("JHFS+", args)

    @patch('subprocess.run')
    def test_partitioner_failure(self, mock_run):
        """Test partitioner handles failure gracefully"""
        disk_id = "disk9"
        installers = [{
            'name': 'Install macOS Sonoma.app',
            'version': '14.6.1',
            'size_kb': 14000000
        }]

        # Mock failure
        mock_run.side_effect = subprocess.CalledProcessError(1, ['cmd'])

        success = partitioner.create_multiboot_layout(disk_id, installers, 64.0)
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
