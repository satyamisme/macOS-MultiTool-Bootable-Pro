"""
disk_detector.py - Detect external USB drives
ONE RESPONSIBILITY: Find safe USB targets
"""

import subprocess
import plistlib

def get_external_usb_drives(show_all=False):
    """
    Get list of external, removable USB drives.

    Args:
        show_all: If True, show all non-boot physical disks (including Internal).

    Returns:
        list: USB drive metadata dicts
    """
    try:
        # Determine list scope
        # Fallback mechanism for diskutil listing
        cmds_to_try = []

        if show_all:
            # Most permissive: All physical disks
            cmds_to_try.append(["diskutil", "list", "physical", "-plist"])
        else:
            # Standard: External physical
            cmds_to_try.append(["diskutil", "list", "external", "physical", "-plist"])
            # Fallback 1: Just External (if 'physical' arg fails on old macOS)
            cmds_to_try.append(["diskutil", "list", "external", "-plist"])

        output = None
        for cmd in cmds_to_try:
            try:
                output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
                break
            except subprocess.CalledProcessError:
                continue

        if output is None:
            # Last resort: List EVERYTHING and filter in Python
            try:
                output = subprocess.check_output(["diskutil", "list", "-plist"])
            except:
                print("Critical: diskutil failed completely.")
                return []

        disk_data = plistlib.loads(output)
    except Exception as e:
        print(f"Error listing disks: {e}")
        return []

    # Get boot disk to exclude it (CRITICAL SAFETY)
    boot_disk_id = _get_boot_disk_id()

    usb_drives = []

    for disk_entry in disk_data.get('AllDisksAndPartitions', []):
        disk_id = disk_entry['DeviceIdentifier']

        # Safety checks - NEVER SKIP THIS
        if _is_unsafe_disk(disk_id, boot_disk_id):
            continue

        # Get detailed disk info
        disk_info = _get_disk_info(disk_id)
        if not disk_info:
            continue

        # Validate criteria
        if not show_all:
            if not _is_valid_usb(disk_info):
                continue
        else:
            # Even in show_all, exclude Virtual disks (DMGs) if they snuck in
            if disk_info.get('Virtual', False):
                continue

        usb_drives.append({
            'id': disk_id,
            'name': disk_info.get('MediaName', 'Unknown'),
            'size_gb': disk_info.get('TotalSize', 0) / 1e9,
            'protocol': disk_info.get('BusProtocol', 'Unknown'),
            'removable': disk_info.get('Removable', False),
            'internal': disk_info.get('Internal', False)
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
    # Never touch disk0 or disk1 (System/Recovery usually)
    # This is a hardcoded safety net.
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
    # If Internal is True, we generally skip unless show_all override was passed (handled in caller)
    if disk_info.get('Internal', True):
        pass

    # Protocol check
    protocol = disk_info.get('BusProtocol', '').lower()
    valid_protocols = ['usb', 'thunderbolt', 'firewire', 'sd', 'mmc']
    is_valid_protocol = any(p in protocol for p in valid_protocols)

    # Check removable flag
    is_removable = disk_info.get('Removable', False)

    # RELAXED RULES:

    # 1. If protocol is explicitly USB/SD/MMC, trust it even if marked Internal
    if is_valid_protocol:
        return True

    # 2. If it's removable, trust it.
    if is_removable:
        return True

    # 3. If we are listing "external" disks (default cmd), and it's not Virtual...
    if disk_info.get('Virtual', False):
        return False

    # If we are here, and Internal=True, and Protocol=SATA... it's probably a real internal drive.
    # We should return False here. The user must enable "Show All" to see it.

    if disk_info.get('Internal', True):
        return False

    return True
