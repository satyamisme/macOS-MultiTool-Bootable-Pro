"""
test_updater.py - Tests for the updater logic
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from operations import updater

class TestUpdater(unittest.TestCase):

    @patch('subprocess.check_output')
    def test_get_drive_structure(self, mock_output):
        """Test parsing of diskutil plist output."""

        # Mock plist output for a disk with existing installers and data store
        # IMPORTANT: plistlib.loads expects bytes, and if it fails, get_drive_structure catches Exception and returns None.
        # The indentation in the triple-quoted string might be causing parsing issues if not stripped,
        # or the plist content itself is somehow invalid for plistlib in this context.
        # Let's clean it up.
        mock_output.return_value = b"""<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>AllDisksAndPartitions</key>
            <array>
                <dict>
                    <key>DeviceIdentifier</key>
                    <string>disk2</string>
                    <key>Size</key>
                    <integer>64000000000</integer>
                    <key>Partitions</key>
                    <array>
                        <dict>
                            <key>DeviceIdentifier</key>
                            <string>disk2s1</string>
                            <key>VolumeName</key>
                            <string>EFI</string>
                        </dict>
                        <dict>
                            <key>DeviceIdentifier</key>
                            <string>disk2s2</string>
                            <key>VolumeName</key>
                            <string>Install macOS Sonoma</string>
                        </dict>
                        <dict>
                            <key>DeviceIdentifier</key>
                            <string>disk2s3</string>
                            <key>VolumeName</key>
                            <string>DATA_STORE</string>
                            <key>Size</key>
                            <integer>10000000000</integer>
                        </dict>
                    </array>
                </dict>
            </array>
        </dict>
        </plist>
        """

        structure = updater.get_drive_structure("disk2")

        self.assertIsNotNone(structure)
        self.assertEqual(structure['disk_size'], 64000000000)
        self.assertEqual(structure['data_partition']['id'], 'disk2s3')
        self.assertEqual(structure['existing_installers'], ['Install macOS Sonoma'])

    @patch('subprocess.run')
    def test_delete_partition(self, mock_run):
        """Test partition deletion logic."""
        mock_run.return_value = MagicMock(returncode=0)

        result = updater.delete_partition("disk2s3")

        self.assertTrue(result)
        mock_run.assert_called_with(
            ['sudo', 'diskutil', 'eraseVolume', 'FREE', '%noformat%', 'disk2s3'],
            check=True,
            capture_output=True
        )

if __name__ == '__main__':
    unittest.main()
