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
    search_term = prompts.prompt_text("Enter macOS name or version to download (e.g., 'Sonoma', '14.6'):")
    if not search_term:
        return

    if mist_downloader.download_installer(search_term):
        display.print_success(f"Successfully downloaded installer matching '{search_term}'")
        display.print_info("You can now use 'Create New Multi-Boot USB' to install it.")
    else:
        display.print_error("Download failed.")
