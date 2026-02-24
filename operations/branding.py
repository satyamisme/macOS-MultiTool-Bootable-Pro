"""
branding.py - Apply icons and boot labels to volumes
ONE RESPONSIBILITY: Make boot menu look professional
ZERO BUGS: Icon extraction happens BEFORE createinstallmedia destroys .app
"""

import os
import subprocess
import tempfile
import atexit

# Global icon cache to survive createinstallmedia
_icon_cache = {}

def extract_icon_from_installer(installer_path, installer_name):
    """
    Extract icon BEFORE createinstallmedia runs.

    Args:
        installer_path: Path to Install macOS.app
        installer_name: Friendly name for caching

    Returns:
        str: Path to cached icon file, or None
    """
    icon_source = os.path.join(
        installer_path,
        "Contents/Resources/ProductPageIcon.icns"
    )

    # Fallback icon names
    if not os.path.exists(icon_source):
        icon_source = os.path.join(
            installer_path,
            "Contents/Resources/InstallAssistant.icns"
        )

    if not os.path.exists(icon_source):
        print(f"  ⚠️  No icon found in installer: {installer_name}")
        return None

    try:
        # Cache to temp directory
        temp_icon = os.path.join(
            tempfile.gettempdir(),
            f"multiboot_icon_{installer_name.replace(' ', '_')}.icns"
        )

        subprocess.run(
            ['cp', icon_source, temp_icon],
            check=True,
            capture_output=True
        )

        _icon_cache[installer_name] = temp_icon
        return temp_icon

    except Exception as e:
        print(f"  ⚠️  Could not extract icon: {e}")
        return None

def apply_icon_to_volume(volume_path, installer_name):
    """
    Apply cached icon to volume AFTER createinstallmedia.
    """
    cached_icon = _icon_cache.get(installer_name)

    if not cached_icon or not os.path.exists(cached_icon):
        return False

    try:
        # Copy icon to volume root
        volume_icon = os.path.join(volume_path, ".VolumeIcon.icns")

        subprocess.run(
            ['sudo', 'cp', cached_icon, volume_icon],
            check=True,
            capture_output=True
        )

        # Set custom icon attribute (requires SetFile from Xcode tools)
        result = subprocess.run(
            ['which', 'SetFile'],
            capture_output=True
        )

        if result.returncode == 0:
            # Set the 'C' (Custom Icon) bit on the Volume root
            subprocess.run(
                ['sudo', 'SetFile', '-a', 'C', volume_path],
                capture_output=True
            )
        else:
            print(f"  ⚠️  SetFile not found (Xcode tools not installed). Icon may not appear.")

        return True

    except Exception as e:
        print(f"  ⚠️  Could not apply icon: {e}")
        return False

def rename_volume(volume_path, new_name):
    """
    Rename the volume to something cleaner.
    """
    try:
        cmd = ['diskutil', 'rename', volume_path, new_name]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"  ⚠️  Could not rename volume: {e}")
        return False

def find_bless_folder(volume_path):
    """
    Locate the folder containing boot.efi or SystemVersion.plist to bless.
    """
    # Standard paths (Newer macOS / Standard Structure)
    candidates = [
        os.path.join(volume_path, "System/Library/CoreServices"),
        os.path.join(volume_path, "Library/CoreServices"),
        os.path.join(volume_path, ".IABootFiles"), # Sometimes hidden
        volume_path # Root fallback?
    ]

    for path in candidates:
        if os.path.exists(os.path.join(path, "boot.efi")):
            return path

    # Deep search if standard paths fail (e.g. High Sierra oddity)
    # createinstallmedia for High Sierra puts files at root but sometimes structure varies.
    try:
        # Use find to locate boot.efi (limit depth to avoid huge search)
        cmd = ['find', volume_path, '-name', 'boot.efi', '-maxdepth', '4']
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
        if output:
            return os.path.dirname(output.split('\n')[0])
    except:
        pass

    return None

def bless_volume(volume_path, os_name, version):
    """
    Bless volume for boot and set label.
    """
    bless_folder = find_bless_folder(volume_path)

    if not bless_folder:
        print(f"  ⚠️  Could not find bootable folder (CoreServices) in {volume_path}")
        return False

    # Create a clean label
    clean_os_name = os_name.replace("Install ", "").replace("macOS ", "")
    label = f"macOS {clean_os_name} {version}"

    try:
        # Bless the folder
        subprocess.run(
            [
                'sudo', 'bless',
                '--folder', bless_folder,
                '--label', label
            ],
            check=True,
            capture_output=True
        )

        return True

    except Exception as e:
        print(f"  ⚠️  Could not bless volume: {e}")
        return False

def apply_full_branding(volume_path, installer_name, os_name, version):
    """
    Apply both icon and blessing to volume.
    """
    print(f"  Applying branding...")

    icon_ok = apply_icon_to_volume(volume_path, installer_name)
    bless_ok = bless_volume(volume_path, os_name, version)

    if icon_ok and bless_ok:
        print(f"  ✓ Branding applied successfully")
    elif icon_ok:
        print(f"  ✓ Icon applied (blessing failed)")
    elif bless_ok:
        print(f"  ✓ Blessing applied (icon failed)")
    else:
        print(f"  ⚠️  Branding partially failed")

def cleanup_icon_cache():
    """Remove temporary icon files."""
    for icon_path in _icon_cache.values():
        try:
            if os.path.exists(icon_path):
                os.remove(icon_path)
        except:
            pass
    _icon_cache.clear()

# Register cleanup on exit
atexit.register(cleanup_icon_cache)
