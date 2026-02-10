"""
boot_disk_guard.py - Prevent accidental boot disk modification
ONE RESPONSIBILITY: Validate disk safety
"""

import subprocess
import plistlib

def is_boot_disk(disk_id):
    """
    Check if disk is the boot disk.

    Args:
        disk_id: Disk identifier (e.g., "disk2")

    Returns:
        bool: True if it's the boot disk
    """
    try:
        # Get boot volume info
        boot_output = subprocess.check_output([
            'diskutil', 'info', '-plist', '/'
        ])
        boot_data = plistlib.loads(boot_output)
        boot_disk_id = boot_data.get('ParentWholeDisk', 'disk0')

        return disk_id == boot_disk_id

    except:
        # If we can't determine, assume it's unsafe
        return True

def has_mounted_system_volume(disk_id):
    """Check if any partition on disk is mounted as system volume."""
    try:
        # Get all partitions
        output = subprocess.check_output([
            'diskutil', 'list', '-plist', disk_id
        ])
        disk_data = plistlib.loads(output)

        for partition_dict in disk_data.get('AllDisksAndPartitions', []):
            for partition in partition_dict.get('Partitions', []):
                part_id = partition['DeviceIdentifier']

                # Check mount point
                part_output = subprocess.check_output([
                    'diskutil', 'info', '-plist', part_id
                ])
                part_data = plistlib.loads(part_output)
                mount_point = part_data.get('MountPoint', '')

                # Check if it's a system mount
                if mount_point in ['/', '/System', '/Library', '/private']:
                    return True

        return False

    except:
        # If we can't determine, assume it's unsafe
        return True

def validate_safe_target(disk_id):
    """
    Comprehensive safety validation.

    Returns:
        tuple: (is_safe: bool, reason: str)
    """
    # Check if it's disk0 or disk1
    if disk_id in ['disk0', 'disk1']:
        return (False, "disk0 and disk1 are never safe targets")

    # Check if it's boot disk
    if is_boot_disk(disk_id):
        return (False, "This is the boot disk")

    # Check if has system volumes
    if has_mounted_system_volume(disk_id):
        return (False, "Disk contains mounted system volumes")

    return (True, "Safe to proceed")
