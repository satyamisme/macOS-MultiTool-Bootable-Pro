import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import plistlib

sys.path.append(os.getcwd())
from detection import disk_detector

class TestDiskDetector(unittest.TestCase):

    @patch('subprocess.run')
    def test_get_external_usb_drives(self, mock_run):
        # Sample plist output for diskutil list external physical -plist
        sample_plist = {
            'AllDisksAndPartitions': [
                {
                    'DeviceIdentifier': 'disk2',
                    'Content': 'GUID_partition_scheme',
                    'Size': 32000000000,
                    'Partitions': []
                }
            ]
        }

        # Mock responses
        # First call: diskutil list external physical -plist
        mock_proc = MagicMock()
        mock_proc.stdout = plistlib.dumps(sample_plist)
        mock_run.return_value = mock_proc

        # Second call: diskutil info -plist /
        # This is called by _get_boot_disk_id
        # We need to patch check_output too or handle it

        # Actually, let's mock subprocess.check_output too
        with patch('subprocess.check_output') as mock_check_output:
            # Mock boot disk check
            boot_plist = {'ParentWholeDisk': 'disk0'}

            # Mock disk info check
            info_plist = {
                'DeviceIdentifier': 'disk2',
                'MediaName': 'MyUSB',
                'TotalSize': 32000000000,
                'BusProtocol': 'USB',
                'SolidState': True,
                'Removable': True,
                'Internal': False,
                'Virtual': False
            }

            def side_effect(cmd, **kwargs):
                if 'info' in cmd and '/' in cmd: # Boot disk check
                    return plistlib.dumps(boot_plist)
                if 'info' in cmd and 'disk2' in cmd:
                    return plistlib.dumps(info_plist)
                return b''

            mock_check_output.side_effect = side_effect

            drives = disk_detector.get_external_usb_drives()

            self.assertEqual(len(drives), 1)
            self.assertEqual(drives[0]['id'], 'disk2')
            self.assertEqual(drives[0]['name'], 'MyUSB')
            self.assertEqual(drives[0]['protocol'], 'USB')
            self.assertEqual(drives[0]['media_type'], 'SSD')

if __name__ == '__main__':
    unittest.main()
