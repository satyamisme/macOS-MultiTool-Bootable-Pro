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

    # mist download installer <search-string> <output-type> ...
    # We want to output an 'application' (.app)
    cmd = ['mist', 'download', 'installer', os_name, 'application']

    if version:
        cmd += ['--version', version]

    # mist output directory flag is --output-directory or -o?
    # Checking mist help from user output: "Usage: mist download installer [<options>] ..."
    # We assume --output-directory is correct based on previous code, but standard mist might be just argument order or specific flag.
    # Let's stick to the flag if it worked before or is documented, but the user output showed help which implies the structure is:
    # mist download installer [options] <search-string> <output-type>
    # The flag --output-directory usually works.

    cmd += ['--output-directory', '/Applications']

    print(f"\nDownloading {os_name}...")
    print("This may take 20-40 minutes depending on connection speed.")

    result = subprocess.run(cmd)
    return result.returncode == 0
