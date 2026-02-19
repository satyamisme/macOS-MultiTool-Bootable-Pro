"""
installer_scanner.py - Scan filesystem for macOS installers
ONE RESPONSIBILITY: Find .app installer files
"""

import os
import subprocess
import plistlib

DEFAULT_SEARCH_PATHS = [
    "/Applications",
    "/Applications/Utilities",
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/Desktop")
]

from typing import List, Dict, Optional, Any

def scan_for_installers(search_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Scan filesystem for macOS installer applications.

    Args:
        search_paths: List of directories to scan (optional)

    Returns:
        list: Found installer metadata dicts
    """
    if search_paths is None:
        search_paths = DEFAULT_SEARCH_PATHS

    found_installers = []
    seen_paths = set()  # Prevent duplicates from symlinks

    for search_dir in search_paths:
        if not os.path.exists(search_dir):
            continue

        try:
            items = os.listdir(search_dir)
        except PermissionError:
            continue

        for item in items:
            if not (item.endswith(".app") and "Install" in item):
                continue

            full_path = os.path.join(search_dir, item)
            real_path = os.path.realpath(full_path)

            # Skip duplicates
            if real_path in seen_paths:
                continue

            # Skip non-directories
            if not os.path.isdir(real_path):
                continue

            seen_paths.add(real_path)

            # Extract metadata
            metadata = _extract_installer_metadata(real_path)
            if metadata:
                found_installers.append(metadata)

    # Also scan for partials
    partials = scan_for_partial_downloads(search_paths)
    found_installers.extend(partials)

    return found_installers

def scan_for_partial_downloads(search_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Scan for partial/failed downloads (e.g., .download bundles or mist temp folders).
    """
    # Clone list to avoid modifying input
    paths = list(search_paths) if search_paths else list(DEFAULT_SEARCH_PATHS)

    # Add mist temp path if likely
    mist_temp = "/private/tmp/com.ninxsoft.mist"
    if os.path.exists(mist_temp) and mist_temp not in paths:
        paths.append(mist_temp)

    partial_installers = []

    for search_dir in paths:
        if not os.path.exists(search_dir): continue

        try:
            items = os.listdir(search_dir)
        except PermissionError: continue

        for item in items:
            full_path = os.path.join(search_dir, item)

            # Check for .download (App Store / Software Update partials)
            if item.endswith(".app.download"):
                partial_installers.append({
                    'name': item.replace(".download", ""),
                    'path': full_path,
                    'version': "Partial",
                    'size_kb': 0,
                    'bundle_id': 'partial.download',
                    'status': 'PARTIAL'
                })

            # Check for Mist temp directories (simple heuristic)
            if "com.ninxsoft.mist" in search_dir and os.path.isdir(full_path):
                 partial_installers.append({
                    'name': f"Mist Download: {item}",
                    'path': full_path,
                    'version': "In Progress",
                    'size_kb': 0,
                    'bundle_id': 'mist.download',
                    'status': 'DOWNLOADING'
                })

    return partial_installers

def _extract_installer_metadata(app_path):
    """Extract version and size from installer .app"""
    try:
        # Read Info.plist
        plist_path = os.path.join(app_path, "Contents/Info.plist")
        with open(plist_path, 'rb') as f:
            plist_data = plistlib.load(f)

        version = plist_data.get("CFBundleShortVersionString", "Unknown")
        bundle_id = plist_data.get("CFBundleIdentifier", "")

        # Validate it's actually a macOS installer
        if "InstallAssistant" not in bundle_id and "Install" not in os.path.basename(app_path):
            return None

        # Get size using du
        try:
            size_kb = int(subprocess.check_output(
                ['du', '-sk', app_path],
                stderr=subprocess.DEVNULL
            ).split()[0])
        except:
            size_kb = 0

        # Determine status
        # We need to import stub_validator here or pass logic.
        # Ideally scan just returns metadata, caller determines status.
        # But we want to flag "Partial".

        status = "UNKNOWN"
        # Check for .download extension? No, this scans .app.

        return {
            'name': os.path.basename(app_path),
            'path': app_path,
            'version': version,
            'size_kb': size_kb,
            'bundle_id': bundle_id,
            # Status will be populated by caller using stub_validator
        }

    except Exception as e:
        return None
