"""
download_mode.py - Download macOS installers via Mist
"""

import sys
from ui import display, prompts
from integration import mist_downloader
import subprocess

def mode_download_installer():
    """Mode 3: Download macOS installer."""
    display.print_header("DOWNLOAD macOS INSTALLER")

    if not mist_downloader.check_mist_available():
        display.print_warning("Mist-CLI is not installed.")
        if not prompts.prompt_yes_no("Install mist-cli now?", 'y'):
            return
        mist_downloader.install_mist()

    print("\nListing available installers (this may take a moment)...")
    try:
        # Run mist list installer to get available versions
        # We assume mist is available now
        subprocess.run(['mist', 'list', 'installer'])
    except Exception as e:
        display.print_error(f"Failed to list installers: {e}")
        return

    print("\n")
    search_term = prompts.prompt_text("Enter macOS names/versions (comma-separated, e.g. 'Sonoma, Ventura'):")
    if not search_term:
        return

    # Split by comma and strip
    targets = [t.strip() for t in search_term.split(',') if t.strip()]

    if mist_downloader.download_installer(targets):
        display.print_success(f"Successfully downloaded: {', '.join(targets)}")
        display.print_info("You can now use 'Create New Multi-Boot USB' to install them.")
    else:
        display.print_error("One or more downloads failed.")
