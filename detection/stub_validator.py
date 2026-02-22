"""
stub_validator.py - Validate if installer is stub or full
ONE RESPONSIBILITY: Check installer completeness
"""

import os
import subprocess

# Thresholds in MB
STUB_THRESHOLD_MB = 50
MINIMUM_SHARED_SUPPORT_MB = 100

def is_stub_installer(app_path):
    """
    Check if installer is a stub (incomplete).

    Args:
        app_path: Path to Install macOS.app

    Returns:
        bool: True if stub, False if full installer
    """
    is_full = False

    # 1. Check SharedSupport.dmg (Modern macOS)
    shared_support = os.path.join(
        app_path,
        "Contents/SharedSupport/SharedSupport.dmg"
    )

    if os.path.exists(shared_support):
        size_mb = os.path.getsize(shared_support) / (1024 * 1024)
        if size_mb > STUB_THRESHOLD_MB:
            return False  # It has a large SharedSupport.dmg, so it's FULL.

    # 2. Check BaseSystem.dmg (Older macOS like High Sierra)
    base_system = os.path.join(
        app_path,
        "Contents/SharedSupport/BaseSystem.dmg"
    )

    if os.path.exists(base_system):
        size_mb = os.path.getsize(base_system) / (1024 * 1024)
        if size_mb > STUB_THRESHOLD_MB:
            return False  # BaseSystem exists and is large enough.

    # 3. Check InstallESD.dmg (Even older, Lion/Mountain Lion)
    install_esd = os.path.join(
        app_path,
        "Contents/SharedSupport/InstallESD.dmg"
    )

    if os.path.exists(install_esd):
        size_mb = os.path.getsize(install_esd) / (1024 * 1024)
        if size_mb > STUB_THRESHOLD_MB:
            return False

    # 4. Fallback: Check Total Bundle Size
    # If any internal component check failed or was skipped, check the total size.
    # A full installer is typically > 4GB.
    try:
        # Check for alternate location: Contents/SharedSupport.dmg (rare but possible)
        alt_shared_support = os.path.join(app_path, "Contents/SharedSupport.dmg")
        if os.path.exists(alt_shared_support) and os.path.getsize(alt_shared_support) > 4 * 1024 * 1024 * 1024:
            return False

        # Check total bundle size using du
        output = subprocess.check_output(
            ['du', '-sk', app_path],
            stderr=subprocess.DEVNULL,
            encoding='utf-8' # Ensure string output
        )
        total_size_kb = int(output.split()[0])
        total_size_mb = total_size_kb / 1024

        if total_size_mb > 4000:  # 4GB
            return False

    except Exception as e:
        # If du fails, we can't determine size.
        # Since specific file checks failed, we assume it's a stub.
        pass

    return True

def get_stub_reason(app_path):
    """Get human-readable reason why installer is stub."""
    # Check total size first as it's the ultimate fallback
    try:
        output = subprocess.check_output(
            ['du', '-sk', app_path],
            stderr=subprocess.DEVNULL,
            encoding='utf-8'
        )
        total_size_kb = int(output.split()[0])
        total_size_mb = total_size_kb / 1024

        if total_size_mb < 4000:
             return f"Total size too small ({total_size_mb:.1f} MB)"
    except:
        pass

    return "Missing payload (SharedSupport.dmg/BaseSystem.dmg)"
