"""
partitioner.py - Create GPT partition layouts
ONE RESPONSIBILITY: Partition disks
"""

import subprocess
from core import constants

def create_multiboot_layout(disk_id, installers, total_disk_gb):
    """
    Create GPT partition layout for multi-boot USB.

    Args:
        disk_id: Target disk (e.g., "disk3")
        installers: List of installer metadata dicts
        total_disk_gb: Total disk size in GB

    Returns:
        bool: True if successful
    """
    # Build partition list
    partitions = []
    used_gb = 0

    # 1. EFI partition (1GB)
    # Using JHFS+ for compatibility, though actual ESP is usually FAT32.
    # diskutil GPT usually creates a hidden ESP at s1.
    # If we specify EFI_SYSTEM as the first user partition, it becomes s2.
    # The user asked for an explicit EFI/Boot partition structure.
    partitions.extend(["JHFS+", "EFI_SYSTEM", "1G"])
    used_gb += 1

    # 2. macOS installer partitions
    for installer in installers:
        # Check for custom buffer injected by GUI
        custom_buffer = installer.get('buffer_gb')

        size_gb = constants.calculate_partition_size(
            installer['size_kb'],
            installer['version'],
            override_buffer_gb=custom_buffer
        )

        # Generate partition name
        os_name = constants.get_os_name(installer['version'])
        version_clean = installer['version'].replace('.', '_').split()[0]
        part_name = f"INSTALL_{os_name}_{version_clean}"[:27]  # Limit length

        partitions.extend(["JHFS+", part_name, f"{size_gb}G"])
        used_gb += size_gb

    # 3. Data partition (remaining space)
    remaining_gb = total_disk_gb - used_gb
    if remaining_gb > 2:
        partitions.extend(["ExFAT", "DATA_STORE", "R"])  # R = remaining

    # Build command
    cmd = [
        "sudo", "diskutil", "partitionDisk",
        f"/dev/{disk_id}",
        "GPT"
    ] + partitions

    print(f"\nExecuting: {' '.join(cmd[:10])}... ({len(partitions)//3} partitions)")

    # Execute
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        print("✓ Partitioning successful!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Partitioning failed!")
        print(f"Error: {e.stderr}")
        return False

def get_partition_list(disk_id):
    """
    Get list of partitions on disk.

    Returns:
        list: Partition info dicts
    """
    import plistlib

    try:
        output = subprocess.check_output([
            'diskutil', 'list', '-plist', disk_id
        ])
        data = plistlib.loads(output)

        partitions = []
        for disk_dict in data.get('AllDisksAndPartitions', []):
            for part in disk_dict.get('Partitions', []):
                partitions.append({
                    'id': part['DeviceIdentifier'],
                    'name': part.get('VolumeName', 'Unnamed'),
                    'size': part.get('Size', 0)
                })

        return partitions

    except:
        return []
