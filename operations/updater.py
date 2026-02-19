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

def delete_partition(part_id):
    """
    Delete a partition to free up space.

    Args:
        part_id: Partition identifier (e.g., "disk2s5")

    Returns:
        bool: True if successful
    """
    print(f"  Deleting partition {part_id}...")
    try:
        # "eraseVolume FREE %noformat% <device>" turns it into free space
        subprocess.run(
            ['sudo', 'diskutil', 'eraseVolume', 'FREE', '%noformat%', part_id],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to delete partition: {e}")
        return False

def add_partitions(disk_id, new_installers):
    """
    Add partitions for new installers into free space.

    Args:
        disk_id: Base disk identifier
        new_installers: List of installer metadata

    Returns:
        list: List of new partition mount points or identifiers
    """
    new_partitions = []

    for installer in new_installers:
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
            # diskutil addPartition <DiskIdentifier> <Filesystem> <Name> <Size>
            # We add to the main disk; diskutil finds the free space at the end
            cmd = [
                'sudo', 'diskutil', 'addPartition',
                disk_id,
                'JHFS+',
                part_name,
                f"{size_gb}G"
            ]

            # This output needs parsing to find the new identifier
            result = subprocess.check_output(cmd, text=True)

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
