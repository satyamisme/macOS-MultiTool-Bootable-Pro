"""
constants.py - macOS version database with buffer allocations
ONE RESPONSIBILITY: Store OS metadata
"""

import math

# macOS version database
OS_DATABASE = {
    "15": {"name": "Sequoia", "buffer_gb": 2.5, "min_year": 2024},
    "14": {"name": "Sonoma", "buffer_gb": 2.2, "min_year": 2023},
    "13": {"name": "Ventura", "buffer_gb": 2.0, "min_year": 2022},
    "12": {"name": "Monterey", "buffer_gb": 2.0, "min_year": 2021},
    "11": {"name": "Big Sur", "buffer_gb": 2.0, "min_year": 2020},
    "10.15": {"name": "Catalina", "buffer_gb": 1.5, "min_year": 2019},
    "10.14": {"name": "Mojave", "buffer_gb": 1.5, "min_year": 2018},
    "10.13": {"name": "High Sierra", "buffer_gb": 1.0, "min_year": 2017},
}

# Filesystem overhead constants
HFS_OVERHEAD_MULTIPLIER = 0.10  # 10% overhead for HFS+
BOOT_FILES_GB = 1.0              # Space for boot files
MIN_PARTITION_GB = 5             # Minimum partition size

def calculate_partition_size(installer_size_kb, version_string):
    """
    Calculate required partition size with future-proof buffer.

    Args:
        installer_size_kb: Installer size in kilobytes
        version_string: macOS version (e.g., "14.6.1")

    Returns:
        int: Required partition size in GB (rounded up)
    """
    # Convert to GB
    installer_gb = float(installer_size_kb) / (1024 * 1024)

    # Get version key
    version_key = _extract_version_key(version_string)

    # Get buffer from database
    os_info = OS_DATABASE.get(version_key, {"buffer_gb": 1.0})
    buffer_gb = os_info["buffer_gb"]

    # Calculate total
    hfs_overhead = installer_gb * HFS_OVERHEAD_MULTIPLIER
    total_gb = installer_gb + hfs_overhead + BOOT_FILES_GB + buffer_gb

    # Round up and enforce minimum
    return max(MIN_PARTITION_GB, math.ceil(total_gb))

def get_os_name(version_string):
    """Get friendly OS name from version string."""
    version_key = _extract_version_key(version_string)
    return OS_DATABASE.get(version_key, {}).get("name", "macOS")

def _extract_version_key(version_string):
    """
    Extract version key for database lookup.
    Handles: "14.6.1", "15.2 Beta", "10.15.7-alpha"
    """
    # Clean version string
    clean = version_string.split()[0].split('-')[0]

    try:
        parts = clean.split('.')

        if parts[0] == "10" and len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"  # "10.15"
        else:
            return parts[0]  # "15"
    except (IndexError, ValueError):
        return "11"  # Default fallback
