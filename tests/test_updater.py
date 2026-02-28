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
        # Structure uses a dict mapping name -> id
        self.assertEqual(structure['existing_installers']['Install macOS Sonoma'], 'disk2s2')

    @patch('subprocess.check_output')
    @patch('operations.updater.get_drive_structure')
    def test_split_partition(self, mock_get_struct, mock_output):
        """Test partition splitting logic."""

        # Mock successful split output
        mock_output.return_value = "Finished partition on disk2s5"

        # Mock drive structure for subsequent splits (recursion case)
        mock_get_struct.return_value = {
            'data_partition': {'id': 'disk2s6'},
            'disk_size': 64000000000,
            'existing_installers': []
        }

        installers = [{
            'name': 'Install macOS Sonoma.app',
            'version': '14.6.1',
            'size_kb': 14000000
        }]

        new_parts = updater.split_partition("disk2s5", installers)

        self.assertEqual(len(new_parts), 1)
        self.assertEqual(new_parts[0]['name'].startswith("INSTALL_Sonoma"), True)

        # Verify call args
        args = mock_output.call_args[0][0]
        self.assertEqual(args[0], 'sudo')
        self.assertEqual(args[1], 'diskutil')
        self.assertEqual(args[2], 'splitPartition')
        self.assertEqual(args[3], 'disk2s5')

if __name__ == '__main__':
    unittest.main()
