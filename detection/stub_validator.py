"""
stub_validator.py - Validate if installer is stub or full
ONE RESPONSIBILITY: Check installer completeness
"""

import os

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
    # Check SharedSupport.dmg
    shared_support = os.path.join(
        app_path,
        "Contents/SharedSupport/SharedSupport.dmg"
    )

    if not os.path.exists(shared_support):
        return True

    size_mb = os.path.getsize(shared_support) / (1024 * 1024)

    # 50MB is safe, but let's be more robust
    if size_mb < STUB_THRESHOLD_MB:
        return True

    # Additional check: BaseSystem.dmg (for older installers)
    base_system = os.path.join(
        app_path,
        "Contents/SharedSupport/BaseSystem.dmg"
    )

    # If neither exists, it's a stub
    if not os.path.exists(base_system) and size_mb < MINIMUM_SHARED_SUPPORT_MB:
        return True

    return False

def get_stub_reason(app_path):
    """Get human-readable reason why installer is stub."""
    shared_support = os.path.join(
        app_path,
        "Contents/SharedSupport/SharedSupport.dmg"
    )

    if not os.path.exists(shared_support):
        return "SharedSupport.dmg missing"

    size_mb = os.path.getsize(shared_support) / (1024 * 1024)

    if size_mb < STUB_THRESHOLD_MB:
        return f"SharedSupport.dmg too small ({size_mb:.1f} MB)"

    return "BaseSystem.dmg missing"
