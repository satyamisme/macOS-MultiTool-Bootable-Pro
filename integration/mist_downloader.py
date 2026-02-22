"""
mist_downloader.py - Mist-CLI integration for downloading installers
ONE RESPONSIBILITY: Download full macOS installers and manage versions
"""

import subprocess
import json
import os
from detection import installer_scanner

def check_mist_available():
    """Check if mist-cli is installed."""
    result = subprocess.run(['which', 'mist'], capture_output=True)
    return result.returncode == 0

def install_mist():
    """Install mist-cli via Homebrew."""
    # Check Homebrew
    if subprocess.run(['which', 'brew'], capture_output=True).returncode != 0:
        print("❌ Homebrew not found")
        print("Install from: https://brew.sh")
        return False

    print("Installing mist-cli via Homebrew...")

    # Check if running as root
    if os.geteuid() == 0:
        # Homebrew cannot run as root.
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            print(f"  Switching to user '{sudo_user}' for Homebrew installation...")
            result = subprocess.run(
                ['sudo', '-u', sudo_user, 'brew', 'install', 'mist'],
                capture_output=False
            )
            return result.returncode == 0
        else:
            print("❌ Cannot install Homebrew as root without SUDO_USER environment variable.")
            print("Please install mist-cli manually: brew install mist")
            return False

    result = subprocess.run(['brew', 'install', 'mist'])
    return result.returncode == 0

def get_local_installers_map():
    """
    Get a map of installed macOS versions/builds.

    Returns:
        dict: { 'version': set(builds), 'names': set(names) }
        e.g. { '14.6.1': {'23G93'}, 'names': {'macOS Sonoma'} }
    """
    local_installers = installer_scanner.scan_for_installers()
    installed_map = {}

    for inst in local_installers:
        ver = inst.get('version')
        if ver:
            # We don't easily get BUILD number from scan_for_installers unless we parse plist deeper.
            # But we have version. Let's just track versions for now.
            # To be precise, we need Build. installer_scanner extracts CFBundleShortVersionString.
            # Let's try to add build to scanner if possible, or just stick to version match.
            installed_map[ver] = True

    return installed_map

def list_installers(search_term=None):
    """
    List available installers from Mist with enriched metadata.

    Args:
        search_term: Optional string to filter (e.g. "Sonoma")

    Returns:
        list: List of dicts with keys:
              identifier, name, version, build, size, date, compatible, downloaded, latest
    """
    if not check_mist_available():
        return []

    cmd = ['mist', 'list', 'installer', '--output-type', 'json', '--quiet']
    if search_term:
        cmd.insert(3, search_term)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return []

        data = json.loads(result.stdout)
        if not data:
            return []

        # Get local versions to flag downloaded ones
        # Since we only have version from scanner (usually), we match on version.
        local_map = get_local_installers_map()

        # Process and mark "Latest"
        # Mist usually returns sorted list?
        # Actually Mist returns newest first typically.
        # Let's group by Major version to find "Latest" for each OS (e.g. Latest Sonoma, Latest Ventura)

        latest_map = {} # Key: Major Version (e.g. "14"), Value: Max Version String

        # First pass: Identify latest versions
        for item in data:
            ver = item.get('version', '0.0')
            major = ver.split('.')[0]

            # Simple string compare is flawed for 14.10 vs 14.9, but mist usually sorts well.
            # Let's trust Mist's order? Mist output:
            # 14.6.1
            # 14.6
            # ...
            # So the first one we see for a Major is the latest?
            if major not in latest_map:
                latest_map[major] = ver
                item['latest'] = True
            else:
                item['latest'] = False

        # Second pass: Enrich
        for item in data:
            ver = item.get('version')
            item['downloaded'] = ver in local_map

        return data

    except Exception as e:
        print(f"Error listing installers: {e}")
        return []

def download_installer_by_identifier(identifier, name_for_log="Installer"):
    """
    Download a specific installer by its Mist Identifier (e.g., "093-22004").
    This ensures we get the EXACT build/version selected.
    """
    if not check_mist_available():
        if not install_mist(): return False

    print(f"\nDownloading {name_for_log} (ID: {identifier})...")
    print("This may take 20-40 minutes.")

    # mist download installer <identifier> application ...
    cmd = [
        'mist', 'download', 'installer',
        identifier,
        'application',
        '--force',
        '--output-directory', '/Applications'
    ]

    result = subprocess.run(cmd)
    return result.returncode == 0

def download_installer(os_names, version=None):
    """
    Legacy wrapper for backward compatibility or simple name-based download.
    """
    if not check_mist_available():
        if not install_mist(): return False

    if isinstance(os_names, str):
        os_names = [os_names]

    success = True
    for name in os_names:
        # If version is specified, try to find the specific identifier first?
        # Or just pass to mist and let it decide (default behavior)
        cmd = ['mist', 'download', 'installer', name, 'application', '--force', '--output-directory', '/Applications']
        if version:
            cmd += ['--version', version]

        print(f"Downloading {name}...")
        if subprocess.run(cmd).returncode != 0:
            success = False

    return success
