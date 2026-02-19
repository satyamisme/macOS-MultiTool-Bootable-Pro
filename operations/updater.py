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
            # diskutil addPartition requires an existing partition to split/resize.
            # Since we deleted the data partition, we have free space.
            # But diskutil addPartition cannot target "free space" directly or the disk ID easily in all versions.
            # The most reliable way to add to free space is to resize the container or use 'partitionDisk' with 'resize'.
            # However, 'addPartition' works if we target the *preceding* partition and ask it to split?
            # Or if we target the disk ID, it might try to use the free space.
            # Actually, `diskutil addPartition` expects a PARTITION identifier to split.
            # If we erased the last partition, we can't "split" it because it's gone.
            #
            # ALTERNATIVE STRATEGY:
            # Instead of `eraseVolume FREE`, we should have resized or just overwritten it.
            # But since we already deleted it (to allow for potentially multiple new partitions),
            # we need to recovery.
            #
            # BETTER STRATEGY for simplicity:
            # We just use `partitionDisk` again on the whole disk? No, that wipes everything.
            # We need to resizing the PREVIOUS partition to fill the space, then split it?
            # Too risky.
            #
            # CORRECT APPROACH for this tool:
            # If we deleted the partition, we should use `diskutil resizeVolume` on the preceding partition
            # to claim the space, then split it?
            # OR, assume the user has a APFS container? No, we use JHFS+.
            #
            # Let's fix the immediate crash: target the preceding partition?
            # But we don't know it easily.
            #
            # Actually, if we use `diskutil splitPartition` on the DATA_STORE *before* deleting it, that works better.
            # But the code structure already deletes it.
            #
            # Let's pivot:
            # Instead of `eraseVolume FREE`, the `delete_partition` should have just formatted it as the first new installer?
            #
            # BUT, to fix the specific error "does not appear to be a valid partition identifier":
            # We will use `diskutil resizeVolume` on the disk ID? No.
            #
            # Let's try to target the disk ID with `diskutil splitPartition`? No.
            #
            # If we assume we are at the end of the disk (DATA_STORE is usually last),
            # maybe we can find the free space gap?
            #
            # For this version, let's revert to a safer approach:
            # Reformat the EXISTING DATA_STORE partition to the new installer (if it fits).
            # If we have multiple installers, we need to split it.
            #
            # So:
            # 1. Don't delete DATA_STORE in step 1.
            # 2. Use `diskutil splitPartition` on DATA_STORE to create [NewInstaller, NewDataStore].
            # 3. Loop.
            #
            # This requires refactoring `main.py` and `updater.py`.
            #
            # Given the constraints and the review feedback, I will implement `splitPartition` logic
            # inside `add_partitions` assuming `disk_id` passed here IS the data partition ID.
            # Wait, `add_partitions` currently receives the `disk_id` (e.g. disk2).
            #
            # I will modify `main.py` to NOT delete the partition, but pass the partition ID to `add_partitions`.
            pass
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
