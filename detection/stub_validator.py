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
        # Final fallback: Check total app size. If > 4GB, it's likely a full installer
        # even if internal structure is non-standard.
        try:
            # Check for alternate location: Contents/SharedSupport.dmg (file directly in Contents)
            alt_shared_support = os.path.join(app_path, "Contents/SharedSupport.dmg")
            if os.path.exists(alt_shared_support) and os.path.getsize(alt_shared_support) > 4 * 1024 * 1024 * 1024:
                return False

            # Check total bundle size using du
            # On macOS, du -sk returns size in 1024-byte blocks
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
            # If du fails, we can't determine size, so assume stub to be safe?
            # Or print debug info? For production, safe default is True (Stub).
            print(f"DEBUG: Stub validation error: {e}")
            pass

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
