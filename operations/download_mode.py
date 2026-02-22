"""
download_mode.py - Download macOS installers via Mist
"""

import sys
import subprocess
from ui import display, prompts
from integration import mist_downloader

def mode_download_installer():
    """Mode 3: Download macOS installer."""
    display.print_header("DOWNLOAD macOS INSTALLER")

    if not mist_downloader.check_mist_available():
        display.print_warning("Mist-CLI is not installed.")
        if not prompts.prompt_yes_no("Install mist-cli now?", 'y'):
            return
        mist_downloader.install_mist()

    print("\nListing available installers (this may take a moment)...")

    # Use new list_installers logic
    # First, list ALL available (or maybe prompt for search term first?
    # Listing ALL can be slow/huge. User usually wants "Sonoma" or "14".
    # But prompt says "Listing available installers...".
    # Mist list without search term lists EVERYTHING available.

    # Let's prompt for search term to filter, defaulting to "latest supported"?
    # Or just list recent ones.

    search_term = prompts.prompt_text("Search (e.g., 'Sonoma', '14', '13.6') [Enter for all]:")

    try:
        installers = mist_downloader.list_installers(search_term)
        if not installers:
            display.print_error("No installers found matching that term.")
            return

        # Print Table
        print("\n" + "="*95)
        print(f"{'#':<4} {'NAME':<25} {'VERSION':<10} {'BUILD':<10} {'SIZE':<10} {'DATE':<12} {'STATUS'}")
        print("="*95)

        for i, inst in enumerate(installers, 1):
            name = inst.get('name', 'Unknown')[:24]
            version = inst.get('version', '0.0')
            build = inst.get('build', '')
            size_bytes = inst.get('size', 0)
            size_gb = f"{size_bytes / (1024**3):.1f} GB"
            date = inst.get('date', '')

            # Status & Latest
            status_flags = []
            if inst.get('downloaded'):
                status_flags.append("✅ Installed")
            if inst.get('latest'):
                status_flags.append("⭐ Latest")

            status_str = " ".join(status_flags)

            print(f"{i:<4} {name:<25} {version:<10} {build:<10} {size_gb:<10} {date:<12} {status_str}")

        print("="*95)

        selection = prompts.prompt_text("\nEnter number(s) to download (e.g., '1, 3'):")
        if not selection:
            return

        indices = [int(s.strip()) for s in selection.split(',') if s.strip().isdigit()]

        to_download = []
        for idx in indices:
            if 1 <= idx <= len(installers):
                to_download.append(installers[idx-1])
            else:
                print(f"Invalid selection: {idx}")

        if not to_download:
            return

        success_count = 0
        for inst in to_download:
            # Use identifier to be exact
            identifier = inst.get('identifier') # Mist JSON usually has identifier? Yes (e.g., "093-22004")
            # But earlier mist versions might not output it in JSON?
            # `mist list installer --output-type json` -> [{"identifier": "...", ...}]

            if identifier:
                if mist_downloader.download_installer_by_identifier(identifier, inst['name']):
                    success_count += 1
            else:
                # Fallback to name/version
                display.print_warning(f"Identifier missing for {inst['name']}, falling back to version...")
                if mist_downloader.download_installer([inst['name']], inst['version']):
                    success_count += 1

        if success_count == len(to_download):
             display.print_success("All downloads completed successfully!")
             display.print_info("You can now use 'Create New Multi-Boot USB' to install them.")
        else:
             display.print_warning("Some downloads failed.")

    except Exception as e:
        display.print_error(f"Failed to list/download installers: {e}")
        import traceback
        traceback.print_exc()
