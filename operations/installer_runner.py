"""
installer_runner.py - Execute Apple's createinstallmedia tool
ONE RESPONSIBILITY: Run installer creation
"""

import subprocess
import os
import time
import re

def run_createinstallmedia(installer_path, volume_path, progress_callback=None):
    """
    Run Apple's createinstallmedia tool.

    Args:
        installer_path: Path to Install macOS.app
        volume_path: Mount point of target volume
        progress_callback: Optional function(percent) for updates

    Returns:
        bool: True if successful
    """
    tool_path = os.path.join(
        installer_path,
        "Contents/Resources/createinstallmedia"
    )

    # Validate tool exists
    if not os.path.exists(tool_path):
        print(f"❌ createinstallmedia not found in installer")
        return False

    # Build command
    cmd = [
        'sudo', tool_path,
        '--volume', volume_path,
        '--nointeraction'
    ]

    print(f"\nRunning createinstallmedia...")
    print(f"  Installer: {os.path.basename(installer_path)}")
    print(f"  Target: {volume_path}")

    start_time = time.time()

    try:
        # Run with real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        last_percent = 0

        for line in process.stdout:
            # Display output
            print(line, end='', flush=True)

            # Parse progress
            if "%" in line:
                try:
                    match = re.search(r'(\d+)%', line)
                    if match:
                        percent = int(match.group(1))
                        if percent != last_percent and progress_callback:
                            progress_callback(percent)
                            last_percent = percent
                except:
                    pass

        process.wait()

        elapsed = time.time() - start_time

        if process.returncode == 0:
            print(f"\n✓ Installation completed in {elapsed/60:.1f} minutes")
            return True
        else:
            print(f"\n❌ Installation failed (code {process.returncode})")
            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def get_volume_mount_point(disk_id, partition_num):
    """
    Get mount point for a partition.

    Args:
        disk_id: Base disk (e.g., "disk3")
        partition_num: Partition number (e.g., 2)

    Returns:
        str: Mount point path or None
    """
    import plistlib

    part_id = f"{disk_id}s{partition_num}"

    try:
        # Ensure partition is mounted
        subprocess.run(
            ['diskutil', 'mount', part_id],
            capture_output=True
        )

        # Get mount point
        output = subprocess.check_output([
            'diskutil', 'info', '-plist', part_id
        ])
        data = plistlib.loads(output)

        return data.get('MountPoint')

    except:
        return None
