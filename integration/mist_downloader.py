"""
mist_downloader.py - Mist-CLI integration for downloading installers
ONE RESPONSIBILITY: Download full macOS installers
"""

import subprocess

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
    import os
    if os.geteuid() == 0:
        # Homebrew cannot run as root.
        # We need to drop privileges or ask user to run manually.
        # Attempt to run as the original user (SUDO_USER)
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

def download_installer(os_name, version=None):
    """
    Download full installer using mist-cli.

    Args:
        os_name: macOS name (e.g., "Sonoma")
        version: Specific version (optional)

    Returns:
        bool: True if successful
    """
    if not check_mist_available():
        print("mist-cli not found")
        if not install_mist():
            return False

    # mist download installer [options] <search-string> <output-type> ...
    # Options must come BEFORE the search string and output type.
    cmd = ['mist', 'download', 'installer']

    # Options
    cmd += ['--force']
    cmd += ['--output-directory', '/Applications']

    if version:
        cmd += ['--version', version]

    # Positional arguments
    cmd += [os_name, 'application']

    print(f"\nDownloading {os_name}...")
    print("This may take 20-40 minutes depending on connection speed.")

    result = subprocess.run(cmd)
    return result.returncode == 0

def get_installer_size(search_term):
    """
    Get the estimated size of an installer from Mist.

    Args:
        search_term: macOS name or version

    Returns:
        int: Size in bytes, or None if not found
    """
    if not check_mist_available():
        return None

    try:
        # mist list installer <search-term> --output-type json
        # Newer mist versions support json output for parsing
        cmd = ['mist', 'list', 'installer', search_term, '--output-type', 'json', '--quiet']
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return None

        import json
        data = json.loads(result.stdout)

        if not data:
            return None

        # Get the first match
        first_match = data[0]
        return first_match.get('size', 0)

    except Exception as e:
        print(f"Error querying mist size: {e}")
        return None
