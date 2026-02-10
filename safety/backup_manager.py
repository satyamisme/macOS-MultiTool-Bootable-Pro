"""
backup_manager.py - Partition table backup and recovery
ONE RESPONSIBILITY: Save/restore disk state
"""

import subprocess
import os
import time

BACKUP_DIR = "/tmp/multiboot_backups"

def backup_partition_table(disk_id):
    """
    Save partition table before destructive operations.

    Args:
        disk_id: Disk to backup

    Returns:
        str: Path to backup file, or None if failed
    """
    # Create backup directory
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Generate backup filename
    timestamp = int(time.time())
    backup_file = os.path.join(
        BACKUP_DIR,
        f"partition_table_{disk_id}_{timestamp}.txt"
    )

    try:
        # Run diskutil list and save output
        with open(backup_file, 'w') as f:
            result = subprocess.run(
                ['diskutil', 'list', disk_id],
                stdout=f,
                stderr=subprocess.PIPE,
                check=True
            )

        print(f"✓ Partition table backed up to: {backup_file}")
        return backup_file

    except Exception as e:
        print(f"⚠️  Warning: Could not backup partition table: {e}")
        return None

def list_backups(disk_id=None):
    """
    List available backups.

    Args:
        disk_id: Filter by disk ID (optional)

    Returns:
        list: Backup file paths
    """
    if not os.path.exists(BACKUP_DIR):
        return []

    backups = []
    for filename in os.listdir(BACKUP_DIR):
        if not filename.startswith('partition_table_'):
            continue

        if disk_id and disk_id not in filename:
            continue

        backups.append(os.path.join(BACKUP_DIR, filename))

    return sorted(backups, reverse=True)

def get_latest_backup(disk_id):
    """Get most recent backup for disk."""
    backups = list_backups(disk_id)
    return backups[0] if backups else None

def display_backup(backup_file):
    """Display backup file contents."""
    try:
        with open(backup_file, 'r') as f:
            print(f.read())
    except:
        print(f"Could not read backup: {backup_file}")
