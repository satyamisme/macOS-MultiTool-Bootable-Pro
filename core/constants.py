"""
constants.py - macOS version database with buffer allocations
ONE RESPONSIBILITY: Store OS metadata
"""

import math

# macOS version database
# buffer_gb: Extra space needed for installation process (temp files, expansion)
OS_DATABASE = {
    "26": {"name": "Tahoe", "buffer_gb": 3.0, "min_year": 2025},
    "15": {"name": "Sequoia", "buffer_gb": 2.5, "min_year": 2024},
    "14": {"name": "Sonoma", "buffer_gb": 2.2, "min_year": 2023},
    "13": {"name": "Ventura", "buffer_gb": 2.0, "min_year": 2022},
    "12": {"name": "Monterey", "buffer_gb": 2.0, "min_year": 2021},
    "11": {"name": "Big Sur", "buffer_gb": 2.0, "min_year": 2020},
    "10.15": {"name": "Catalina", "buffer_gb": 1.5, "min_year": 2019},
    "10.14": {"name": "Mojave", "buffer_gb": 1.5, "min_year": 2018},
    "10.13": {"name": "High Sierra", "buffer_gb": 1.0, "min_year": 2017},
    "10.12": {"name": "Sierra", "buffer_gb": 1.0, "min_year": 2016},
    "10.11": {"name": "El Capitan", "buffer_gb": 1.0, "min_year": 2015},
}

# Filesystem overhead constants (Optimized for density)
HFS_OVERHEAD_MULTIPLIER = 0.05  # Reduced to 5% overhead for HFS+ (Installer volumes are mostly read-only)
BOOT_FILES_MB = 200             # Reduced to 200MB for boot files (EFI/Preboot)
MIN_PARTITION_MB = 5500         # ~5.5GB Minimum

def calculate_partition_size(installer_size_kb: int, version_string: str, override_buffer_gb: float = None) -> int:
    """
    Calculate required partition size with future-proof buffer.

    Args:
        installer_size_kb: Installer size in kilobytes
        version_string: macOS version (e.g., "14.6.1")
        override_buffer_gb: Optional custom safety buffer in GB

    Returns:
        int: Required partition size in MB (rounded up)
    """
    # Convert input to MB
    installer_mb = float(installer_size_kb) / 1024

    # Get buffer (convert GB to MB)
    if override_buffer_gb is not None:
        buffer_mb = override_buffer_gb * 1024
    else:
        # Fallback to database or global default
        version_key = _extract_version_key(version_string)
        default = OS_DATABASE.get("default_buffer", 1.0)
        os_info = OS_DATABASE.get(version_key, {"buffer_gb": default})
        buffer_mb = os_info["buffer_gb"] * 1024

    # Calculate total
    hfs_overhead = installer_mb * HFS_OVERHEAD_MULTIPLIER
    total_mb = installer_mb + hfs_overhead + BOOT_FILES_MB + buffer_mb

    # Round up and enforce minimum
    return max(MIN_PARTITION_MB, math.ceil(total_mb))

def get_os_name(version_string, installer_name=None):
    """
    Get friendly OS name from version string or installer name.
    Prioritizes explicit name mapping if version parsing is ambiguous.
    """
    # 1. Try Name-based lookup first (More reliable for older installers with updated app versions)
    if installer_name:
        clean_name = installer_name.replace("Install macOS ", "").replace("Install ", "").replace(".app", "")
        # Check against DB names
        for key, info in OS_DATABASE.items():
            if info['name'].lower() in clean_name.lower():
                return info['name']

        # Special case for Sierra/El Capitan which might not match exact key
        if "Sierra" in clean_name and "High" not in clean_name: return "Sierra"
        if "High Sierra" in clean_name: return "High Sierra"
        if "El Capitan" in clean_name: return "El Capitan"

    # 2. Fallback to version-based lookup
    version_key = _extract_version_key(version_string)
    return OS_DATABASE.get(version_key, {}).get("name", "macOS")

def _extract_version_key(version_string):
    """
    Extract version key for database lookup.
    Handles: "14.6.1", "15.2 Beta", "10.15.7-alpha", "15.0 Beta 3"
    Also handles updated installer app versions: "13.6.02" (High Sierra 10.13 installer updated in 2020)
    """
    # Clean version string: remove "Beta", "RC", etc.
    # Split by space first, take first part.
    # Then split by hyphen, take first part.
    clean = version_string.split()[0].split('-')[0]

    try:
        parts = clean.split('.')

        # Case 1: Standard "10.xx" (Yosemite to Catalina)
        if parts[0] == "10" and len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"  # "10.15"

        # Case 2: Major versions (Big Sur+)
        # 11, 12, 13, 14, 15...
        if int(parts[0]) >= 11:
            # Check for the High Sierra anomaly where version is "13.6.02" but it's actually 10.13 installer app version
            # This is tricky without the Name.
            # Ideally get_os_name uses the name.
            # Here we just return the major version.
            # If we return "13", it maps to Ventura.
            # This logic flaw is why get_os_name needs to use the Name.
            return parts[0]

        return "11"  # Default fallback
    except (IndexError, ValueError):
        return "11"
