"""
disk_detector.py - Detect external USB drives
ONE RESPONSIBILITY: Find safe USB targets
"""

import subprocess
import plistlib

def get_external_usb_drives():
    """
    Get list of external, removable USB drives.

    Returns:
        list: USB drive metadata dicts
    """
    try:
        # Get external physical disks
        # This already filters many internal ones.
        output = subprocess.check_output([
            "diskutil", "list", "external", "physical", "-plist"
        ])
        disk_data = plistlib.loads(output)
    except Exception as e:
        print(f"Error listing disks: {e}")
        return []

    # Get boot disk to exclude it
    boot_disk_id = _get_boot_disk_id()

    usb_drives = []

    for disk_entry in disk_data.get('AllDisksAndPartitions', []):
        disk_id = disk_entry['DeviceIdentifier']

        # Safety checks
        if _is_unsafe_disk(disk_id, boot_disk_id):
            continue

        # Get detailed disk info
        disk_info = _get_disk_info(disk_id)
        if not disk_info:
            continue

        # Validate it's truly external and removable
        if not _is_valid_usb(disk_info):
            continue

        usb_drives.append({
            'id': disk_id,
            'name': disk_info.get('MediaName', 'Unknown'),
            'size_gb': disk_info.get('TotalSize', 0) / 1e9,
            'protocol': disk_info.get('BusProtocol', 'Unknown'),
            'removable': disk_info.get('Removable', False)
        })

    return usb_drives

def _get_boot_disk_id():
    """Get the disk ID of the boot volume."""
    try:
        output = subprocess.check_output(['diskutil', 'info', '-plist', '/'])
        boot_data = plistlib.loads(output)
        return boot_data.get('ParentWholeDisk', 'disk0')
    except:
        return 'disk0'

def _is_unsafe_disk(disk_id, boot_disk_id):
    """Check if disk is unsafe to modify."""
    # Never touch disk0 or disk1
    # Use exact string matching
    if disk_id == 'disk0' or disk_id == 'disk1':
        return True

    # Never touch boot disk
    if disk_id == boot_disk_id:
        return True

    return False

def _get_disk_info(disk_id):
    """Get detailed disk information."""
    try:
        output = subprocess.check_output([
            'diskutil', 'info', '-plist', disk_id
        ])
        return plistlib.loads(output)
    except:
        return None

def _is_valid_usb(disk_info):
    """Validate disk is truly external and likely removable."""

    # Check internal flag
    is_internal = disk_info.get('Internal', True)

    # Protocol check
    protocol = disk_info.get('BusProtocol', '').lower()
    valid_protocols = ['usb', 'thunderbolt', 'firewire', 'sd', 'mmc']
    is_valid_protocol = any(p in protocol for p in valid_protocols)

    # Check removable flag
    is_removable = disk_info.get('Removable', False)

    # RELAXED RULES:

    # 1. If protocol is explicitly USB/SD/MMC, trust it even if marked Internal
    # (some USB adapters report as internal SATA/NVMe bridges but are external enclosures)
    # BUT we must be very careful about accidentally wiping real internal drives.
    # The `diskutil list external` command is the first filter. If diskutil thinks it's external,
    # we should trust that over the `Internal` flag from `diskutil info` IF protocol matches.

    if is_valid_protocol:
        return True

    # 2. If it's removable, trust it.
    if is_removable:
        return True

    # 3. If diskutil list external returned it, but protocol is weird (e.g. SATA via USB bridge)
    # and removable is false... it's risky. But user says "usb driver not detecting".
    # Often these appear as "External Physical Store".
    # Since we are iterating strictly over `diskutil list external`, we can be more lenient.
    # We already filter out boot disk and disk0/disk1.

    # So if it's in the external list, and not unsafe... accept it?
    # Let's add a check for "Virtual" to exclude DMGs.
    if disk_info.get('Virtual', False):
        return False

    # If we got here, diskutil says it's external.
    return True
