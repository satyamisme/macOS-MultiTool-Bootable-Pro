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
            'existing_installers': {'High Sierra': 'disk2s2', ...}, # Map Name -> ID
            'disk_size': 64000000000,
            'free_space': 0
        }
    """
    info = {
        'data_partition': None,
        'existing_installers': {}, # Changed from list to dict for easier lookup
        'disk_size': 0,
        'free_space': 0
    }

    try:
        # Get full disk info
        output = subprocess.check_output(['diskutil', 'list', '-plist', disk_id])
        data = plistlib.loads(output)

        for entry in data.get('AllDisksAndPartitions', []):
            if entry.get('DeviceIdentifier') == disk_id:
                info['disk_size'] = entry.get('Size', 0)

                used_size = 0
                for partition in entry.get('Partitions', []):
                    vol_name = partition.get('VolumeName', '')
                    part_size = partition.get('Size', 0)
                    part_id = partition.get('DeviceIdentifier')
                    used_size += part_size

                    if vol_name == 'DATA_STORE':
                        info['data_partition'] = {
                            'id': part_id,
                            'size': part_size
                        }
                    elif 'Install macOS' in vol_name or 'INSTALL_' in vol_name or 'macOS' in vol_name:
                        # Try to normalize name to OS name only?
                        # e.g., "Install macOS High Sierra" -> "High Sierra"
                        # Or just store full name map
                        clean_name = vol_name.replace("Install macOS ", "").replace("INSTALL_", "").replace("macOS ", "")
                        # Store flexible keys
                        info['existing_installers'][clean_name] = part_id
                        info['existing_installers'][vol_name] = part_id # Store exact too

                info['free_space'] = info['disk_size'] - used_size

        return info

    except Exception as e:
        print(f"Error scanning drive: {e}")
        return None

def split_partition(part_id, new_installers):
    """
    Split the DATA_STORE partition to create space for new installers.
    """
    current_part = part_id
    new_partitions = []

    for i, installer in enumerate(new_installers):
        custom_buffer = installer.get('buffer_gb')
        size_mb = constants.calculate_partition_size(
            installer['size_kb'],
            installer['version'],
            override_buffer_gb=custom_buffer
        )

        os_name = constants.get_os_name(installer['version'], installer.get('name'))
        version_clean = installer['version'].replace('.', '_').split()[0]
        part_name = f"INSTALL_{os_name}_{version_clean}"[:27]

        print(f"  Adding partition: {part_name} ({size_mb} MB)...")

        try:
            cmd = [
                'sudo', 'diskutil', 'splitPartition',
                current_part,
                '2',
                'JHFS+', part_name, f"{size_mb}M",
                'ExFAT', 'DATA_STORE', 'R'
            ]

            output = subprocess.check_output(cmd, text=True)
            print("  ✓ Split successful")

            new_partitions.append({'name': part_name, 'installer': installer})

            if i < len(new_installers) - 1:
                structure = get_drive_structure(current_part.split('s')[0])
                if structure and structure['data_partition']:
                    current_part = structure['data_partition']['id']
                else:
                    return new_partitions

        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to add partition for {installer['name']}: {e}")
            return None

    return new_partitions

def add_partition_to_free_space(disk_id, new_installers):
    """
    Add partitions to existing free space on the disk.
    """
    new_partitions = []

    for installer in new_installers:
        custom_buffer = installer.get('buffer_gb')
        size_mb = constants.calculate_partition_size(
            installer['size_kb'],
            installer['version'],
            override_buffer_gb=custom_buffer
        )

        os_name = constants.get_os_name(installer['version'], installer.get('name'))
        version_clean = installer['version'].replace('.', '_').split()[0]
        part_name = f"INSTALL_{os_name}_{version_clean}"[:27]

        print(f"  Adding partition to free space: {part_name} ({size_mb} MB)...")

        try:
            cmd = [
                'sudo', 'diskutil', 'addPartition',
                disk_id,
                'JHFS+', part_name, f"{size_mb}M"
            ]

            subprocess.check_output(cmd, text=True)
            print("  ✓ Add successful")
            new_partitions.append({'name': part_name, 'installer': installer})

        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to add partition: {e}")
            return None

    return new_partitions

def replace_existing_partition(part_id, installer):
    """
    Reformat an existing partition to update it.

    Args:
        part_id: The partition identifier (e.g., "disk2s2")
        installer: Installer metadata

    Returns:
        dict: {'name': new_name, 'installer': installer} or None
    """
    os_name = constants.get_os_name(installer['version'], installer.get('name'))
    version_clean = installer['version'].replace('.', '_').split()[0]
    part_name = f"INSTALL_{os_name}_{version_clean}"[:27]

    print(f"  Reformatting {part_id} as {part_name}...")

    try:
        # Check size constraints?
        # Ideally we check if existing partition is big enough.
        # But eraseVolume just uses existing size.
        # If new installer is bigger than old partition + buffer, install might fail later.
        # Warn user in GUI? For now assume user knows or space is sufficient (installers usually similiar size)

        cmd = ['sudo', 'diskutil', 'eraseVolume', 'JHFS+', part_name, part_id]
        subprocess.check_output(cmd, text=True)
        print("  ✓ Reformat successful")
        return {'name': part_name, 'installer': installer}

    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to reformat partition: {e}")
        return None

def restore_data_partition(disk_id):
    try:
        subprocess.run(
            ['sudo', 'diskutil', 'addPartition', disk_id, 'ExFAT', 'DATA_STORE', '0'],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError:
        return False
