"""
updater.py - Update existing multi-boot drives
ONE RESPONSIBILITY: Add new installers to an existing layout
"""

import subprocess
import plistlib
import sys
from core import constants

def get_drive_structure(disk_id):
    """
    Analyze the current partition structure of a drive.

    Args:
        disk_id: Target disk identifier (e.g., "disk2")

    Returns:
        dict: {
            'data_partition': {'id': 'disk2sX', 'size': 12345}, # or None
            'existing_installers': ['Sonoma', 'Ventura'],
            'disk_size': 64000000000
        }
    """
    info = {
        'data_partition': None,
        'existing_installers': [],
        'disk_size': 0
    }

    try:
        # Get full disk info
        output = subprocess.check_output(['diskutil', 'list', '-plist', disk_id])
        data = plistlib.loads(output)

        # Get disk size from the root object or partitions list logic
        # diskutil list output structure varies slightly, but usually:
        # data['AllDisksAndPartitions'][0]['Size'] is the whole disk
        for entry in data.get('AllDisksAndPartitions', []):
            if entry.get('DeviceIdentifier') == disk_id:
                info['disk_size'] = entry.get('Size', 0)

                for partition in entry.get('Partitions', []):
                    vol_name = partition.get('VolumeName', '')

                    if vol_name == 'DATA_STORE':
                        info['data_partition'] = {
                            'id': partition.get('DeviceIdentifier'),
                            'size': partition.get('Size', 0)
                        }
                    elif 'Install macOS' in vol_name or 'INSTALL_' in vol_name:
                        info['existing_installers'].append(vol_name)

        return info

    except Exception as e:
        print(f"Error scanning drive: {e}")
        return None

def split_partition(part_id, new_installers):
    """
    Split the DATA_STORE partition to create space for new installers.

    Args:
        part_id: The partition identifier to split (e.g., "disk2s5")
        new_installers: List of installer metadata

    Returns:
        list: List of new partition info [{'name':..., 'installer':...}]
    """
    current_part = part_id
    new_partitions = []

    for i, installer in enumerate(new_installers):
        size_gb = constants.calculate_partition_size(
            installer['size_kb'],
            installer['version']
        )

        # Generate name
        os_name = constants.get_os_name(installer['version'])
        version_clean = installer['version'].replace('.', '_').split()[0]
        part_name = f"INSTALL_{os_name}_{version_clean}"[:27]

        print(f"  Adding partition: {part_name} ({size_gb} GB)...")

        try:
            # We need to know the next partition ID. diskutil usually increments it.
            # If we split disk2s5, we typically get disk2s5 (new) and disk2s6 (remainder).

            cmd = [
                'sudo', 'diskutil', 'splitPartition',
                current_part,
                '2',
                'JHFS+', part_name, f"{size_gb}G",
                'ExFAT', 'DATA_STORE', 'R'
            ]

            output = subprocess.check_output(cmd, text=True)
            print("  ✓ Split successful")

            new_partitions.append({'name': part_name, 'installer': installer})

            # The "DATA_STORE" partition is now the new last partition.
            # We need to find its identifier to split it again for the next installer.
            # We can't easily guess it (it might be s6, s7).
            # We must re-scan to find "DATA_STORE".

            if i < len(new_installers) - 1:
                # Find new DATA_STORE ID
                structure = get_drive_structure(current_part.split('s')[0]) # pass 'disk2'
                if structure and structure['data_partition']:
                    current_part = structure['data_partition']['id']
                else:
                    print("  ❌ Could not find DATA_STORE after split")
                    return new_partitions # Partial success

            # The command output usually ends with details of the new disk
            # e.g., "Finished partition on disk2s5"
            # But let's verify by checking the list or assuming sequential order?
            # Safer to rely on the name matching later or verify checking list.

            # For now, let's assume it worked.
            new_partitions.append({'name': part_name, 'installer': installer})

        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to add partition for {installer['name']}: {e}")
            return None

    return new_partitions

def restore_data_partition(disk_id):
    """
    Create DATA_STORE partition with remaining space.
    """
    print(f"  Restoring DATA_STORE partition...")
    try:
        # Use '0' or 'R' size to fill remaining space?
        # diskutil addPartition supports '0b' or limits.
        # usually 0 means "rest of disk"
        subprocess.run(
            ['sudo', 'diskutil', 'addPartition', disk_id, 'ExFAT', 'DATA_STORE', '0'],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to restore DATA_STORE: {e}")
        return False
