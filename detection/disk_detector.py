"""
disk_detector.py - Detect external USB drives
ONE RESPONSIBILITY: Find safe USB targets
"""

import subprocess
import plistlib
import sys

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
                print(f"DEBUG: Trying command: {' '.join(cmd)}")
                # Capture stderr to see errors
                proc = subprocess.run(cmd, capture_output=True, check=True)
                output = proc.stdout
                print("DEBUG: Command success")
                break
            except subprocess.CalledProcessError as e:
                print(f"DEBUG: Command failed: {e}")
                print(f"DEBUG: Stderr: {e.stderr}")
                continue

        if output is None:
            # Last resort: List EVERYTHING and filter in Python
            try:
                print("DEBUG: Trying fallback: diskutil list -plist")
                output = subprocess.check_output(["diskutil", "list", "-plist"])
            except Exception as e:
                print(f"Critical: diskutil failed completely: {e}")
                return []

        if not output:
            print("DEBUG: Output empty")
            return []

        try:
            disk_data = plistlib.loads(output)
        except Exception as e:
            print(f"DEBUG: Plist parse error: {e}")
            print(f"DEBUG: Raw output start: {output[:100]}")
            return []

    except Exception as e:
        print(f"Error listing disks: {e}")
        import traceback
        traceback.print_exc()
        return []

    # Get boot disk to exclude it (CRITICAL SAFETY)
    boot_disk_id = _get_boot_disk_id()
    print(f"DEBUG: Boot disk identified as: {boot_disk_id}")

    usb_drives = []

    for disk_entry in disk_data.get('AllDisksAndPartitions', []):
        disk_id = disk_entry['DeviceIdentifier']
        print(f"DEBUG: Checking {disk_id}...")

        # Safety checks - NEVER SKIP THIS
        if _is_unsafe_disk(disk_id, boot_disk_id):
            print(f"DEBUG: Skipped {disk_id} (Unsafe/Boot)")
            continue

        # Get detailed disk info
        disk_info = _get_disk_info(disk_id)
        if not disk_info:
            print(f"DEBUG: Skipped {disk_id} (No Info)")
            continue

        # Validate criteria
        if not show_all:
            if not _is_valid_usb(disk_info):
                print(f"DEBUG: Skipped {disk_id} (Invalid USB check)")
                continue
        else:
            if disk_info.get('Virtual', False):
                print(f"DEBUG: Skipped {disk_id} (Virtual)")
                continue

        print(f"DEBUG: Accepted {disk_id}")

        # Determine media type (SSD/HDD)
        media_type = "HDD"
        if disk_info.get('SolidState', False): media_type = "SSD"

        usb_drives.append({
            'id': disk_id,
            'name': disk_info.get('MediaName', 'Unknown'),
            'size_gb': disk_info.get('TotalSize', 0) / 1e9,
            'protocol': disk_info.get('BusProtocol', 'Unknown'),
            'media_type': media_type,
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
    if disk_id == 'disk0' or disk_id == 'disk1':
        return True
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

    if disk_info.get('Internal', True):
        # Allow internal ONLY if show_all handled upstream?
        # But this function is called when show_all=False.
        # So we should reject internal unless protocol override matches.
        pass

    protocol = disk_info.get('BusProtocol', '').lower()
    valid_protocols = ['usb', 'thunderbolt', 'firewire', 'sd', 'mmc']
    is_valid_protocol = any(p in protocol for p in valid_protocols)

    is_removable = disk_info.get('Removable', False)

    # Debug info
    print(f"DEBUG: {disk_info.get('DeviceIdentifier')} - Proto: {protocol}, Remov: {is_removable}, Int: {disk_info.get('Internal')}")

    if is_valid_protocol: return True
    if is_removable: return True
    if disk_info.get('Virtual', False): return False
    if disk_info.get('Internal', True): return False

    return True
