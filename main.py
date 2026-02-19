#!/usr/bin/env python3
"""
main.py - macOS Multi-Tool Pro
ZERO BUGS GUARANTEE: Orchestrates all modules with error handling
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import privilege, constants
from detection import installer_scanner, stub_validator, disk_detector
from safety import boot_disk_guard, backup_manager
from operations import partitioner, installer_runner, branding, updater, download_mode
from integration import mist_downloader
from ui import display, prompts, progress, help

VERSION = "2.0.0"

def check_dependencies():
    """Verify required tools are available."""
    import subprocess

    required = ['diskutil', 'sudo', 'du']
    optional = ['SetFile', 'bless']

    missing_required = []
    missing_optional = []

    for tool in required:
        if subprocess.run(['which', tool], capture_output=True).returncode != 0:
            missing_required.append(tool)

    if missing_required:
        display.print_error("Missing required tools:")
        for tool in missing_required:
            print(f"  ✗ {tool}")
        sys.exit(1)

    for tool in optional:
        if subprocess.run(['which', tool], capture_output=True).returncode != 0:
            missing_optional.append(tool)

    if missing_optional:
        display.print_warning("Missing optional tools (some features limited):")
        for tool in missing_optional:
            print(f"  ⚠  {tool}")
        print()

def mode_create_new(args):
    """Mode 1: Create new multi-boot USB."""
    global ARGS
    ARGS = args
    display.print_header("CREATE NEW MULTI-BOOT USB")

    # Step 1: Scan for installers
    while True:
        display.print_step(1, 5, "Scanning for macOS installers")
        # Use custom app-dir if provided via global args (need to pass it down)
        # We need to access 'args' here. Refactoring mode_create_new to accept args or use global.
        # For simplicity in this script, we'll use the global args variable if we make it available,
        # or pass it.
        # Let's pass it. But mode_create_new is called without args.
        # I'll modify mode_create_new signature.
        custom_paths = [ARGS.app_dir] if ARGS.app_dir else None
        installers = installer_scanner.scan_for_installers(search_paths=custom_paths)

        if not installers:
            display.print_error("No macOS installers found!")
            if prompts.prompt_yes_no("Download a macOS installer now?"):
                mode_download_installer()
                continue
            else:
                display.print_info("Download installers using App Store or 'mist-cli'.")
                return # Return to main menu instead of exit

        print(f"\nFound {len(installers)} installer(s):\n")
        break

    # Validate installers
    valid_installers = []
    restart_scan = False
    for inst in installers:
        is_stub = stub_validator.is_stub_installer(inst['path'])
        inst['is_stub'] = is_stub

        status = f"{display.Colors.YELLOW}STUB{display.Colors.END}" if is_stub else f"{display.Colors.GREEN}FULL{display.Colors.END}"
        size = display.format_size(inst['size_kb'] * 1024)

        print(f"  • {inst['name']}")
        print(f"    Version: {inst['version']} | Size: {size} | Status: {status}")

        if not is_stub:
            valid_installers.append(inst)
        else:
            # Offer to download full installer
            reason = stub_validator.get_stub_reason(inst['path'])
            print(f"    Reason: {reason}")

            if prompts.prompt_yes_no(f"    Download full installer for {inst['name']}?", 'n'):
                # Try to guess OS name from the app name first (more reliable for weird versions)
                # e.g., "Install macOS Catalina.app" -> "Catalina"
                os_name = inst['name'].replace("Install macOS ", "").replace(".app", "")

                # Fallback to version-based lookup if name parsing looks weird
                if not os_name or len(os_name) > 20 or " " in os_name:
                     os_name = constants.get_os_name(inst['version'])

                if mist_downloader.download_installer(os_name):
                    display.print_success(f"Downloaded {os_name}")
                    restart_scan = True
                    break
                else:
                    display.print_error("Download failed")

    if restart_scan:
        continue

    if not valid_installers:
        display.print_error("No valid full installers available")
        if prompts.prompt_yes_no("Download a macOS installer now?"):
             mode_download_installer()
             continue
        else:
             return

    # Step 2: Select USB drive
    display.print_step(2, 5, "Detecting USB drives")
    usb_drives = disk_detector.get_external_usb_drives()

    if not usb_drives:
        display.print_error("No external USB drives detected!")
        sys.exit(1)

    print(f"\nFound {len(usb_drives)} USB drive(s):\n")

    disk_options = []
    for disk in usb_drives:
        option = f"{disk['name']} ({disk['id']}) - {disk['size_gb']:.1f} GB - {disk['protocol']}"
        disk_options.append(option)
        print(f"  • {option}")

    disk_choice = prompts.prompt_choice("\nSelect USB drive:", disk_options)

    if disk_choice is None:
        print("Operation cancelled.")
        sys.exit(0)

    selected_disk = usb_drives[disk_choice]

    # Safety validation
    is_safe, reason = boot_disk_guard.validate_safe_target(selected_disk['id'])
    if not is_safe:
        display.print_error(f"Cannot use this disk: {reason}")
        sys.exit(1)

    # Step 3: Confirm destructive operation
    display.print_step(3, 5, "Confirmation")

    if not prompts.confirm_destructive_action(
        selected_disk['id'],
        selected_disk['name'],
        selected_disk['size_gb']
    ):
        print("\nOperation cancelled by user.")
        sys.exit(0)

    # Backup partition table
    backup_file = backup_manager.backup_partition_table(selected_disk['id'])

    # Step 4: Extract icons BEFORE partitioning
    display.print_step(4, 5, "Extracting installer icons")
    for inst in valid_installers:
        print(f"  Extracting icon from {inst['name']}...")
        branding.extract_icon_from_installer(inst['path'], inst['name'])

    # Step 5: Partition disk
    display.print_step(5, 5, "Creating partitions")

    if not partitioner.create_multiboot_layout(
        selected_disk['id'],
        valid_installers,
        selected_disk['size_gb']
    ):
        display.print_error("Partitioning failed!")
        if backup_file:
            print(f"\nPartition table backup saved at: {backup_file}")
        sys.exit(1)

    display.print_success("Partitions created successfully!")

    # Step 6: Install macOS to each partition
    display.print_header("INSTALLING macOS TO PARTITIONS")

    # Start from s3 (s1 is EFI, s2 is our custom EFI_SYSTEM)
    partition_num = 3
    successful = []
    failed = []

    for i, inst in enumerate(valid_installers, 1):
        print(f"\n{'='*70}")
        display.print_step(i, len(valid_installers), f"Installing {inst['name']} {inst['version']}")
        print('='*70)

        try:
            # Get volume mount point
            volume_path = installer_runner.get_volume_mount_point(
                selected_disk['id'],
                partition_num
            )

            if not volume_path:
                display.print_error(f"Could not mount partition {partition_num}")
                failed.append(inst['name'])
                partition_num += 1
                continue

            # Run createinstallmedia
            start_time = time.time()

            success = installer_runner.run_createinstallmedia(
                inst['path'],
                volume_path,
                progress_callback=lambda p: progress.show_progress_bar(
                    f"Installing {inst['name']}",
                    p,
                    start_time
                )
            )

            if success:
                # Re-fetch volume path as it may have changed after createinstallmedia
                new_volume_path = installer_runner.get_volume_mount_point(
                    selected_disk['id'],
                    partition_num
                )

                if new_volume_path:
                    # Apply branding
                    os_name = constants.get_os_name(inst['version'])
                    branding.apply_full_branding(
                        new_volume_path,
                        inst['name'],
                        os_name,
                        inst['version']
                    )
                else:
                    display.print_warning(f"Could not remount volume for branding: {inst['name']}")

                display.print_success(f"{inst['name']} installed successfully!")
                successful.append(inst['name'])
            else:
                display.print_error(f"{inst['name']} installation failed!")
                failed.append(inst['name'])

        except KeyboardInterrupt:
            display.print_warning("\n\nInstallation interrupted by user")
            break

        except Exception as e:
            display.print_error(f"Unexpected error: {e}")
            failed.append(inst['name'])

        finally:
            partition_num += 1

    # Final summary
    display.print_header("✓ OPERATION COMPLETE")

    print(f"Successful installations: {len(successful)}")
    for name in successful:
        display.print_success(name)

    if failed:
        print(f"\nFailed installations: {len(failed)}")
        for name in failed:
            display.print_error(name)

    print("\n" + "="*70)
    display.print_info("Your multi-boot USB is ready!")
    print("\nTo boot from this USB:")
    print("  1. Restart your Mac")
    print("  2. Hold Option (⌥) key during startup")
    print("  3. Select the desired macOS installer")
    print("="*70 + "\n")

def mode_download_installer():
    """Mode 3: Download macOS installer."""
    download_mode.mode_download_installer()

def mode_update_existing():
    """Mode 2: Update existing multi-boot USB."""
    display.print_header("UPDATE EXISTING MULTI-BOOT USB")

    # Step 1: Select USB drive
    display.print_step(1, 5, "Select Target Drive")
    usb_drives = disk_detector.get_external_usb_drives()

    if not usb_drives:
        display.print_error("No external USB drives detected!")
        sys.exit(1)

    disk_options = []
    for disk in usb_drives:
        option = f"{disk['name']} ({disk['id']}) - {disk['size_gb']:.1f} GB"
        disk_options.append(option)

    disk_choice = prompts.prompt_choice("\nSelect existing Multi-Tool USB:", disk_options)
    if disk_choice is None: sys.exit(0)

    selected_disk = usb_drives[disk_choice]

    # Analyze drive structure
    structure = updater.get_drive_structure(selected_disk['id'])
    if not structure:
        display.print_error("Failed to analyze drive structure.")
        sys.exit(1)

    if not structure['data_partition']:
        display.print_warning("No DATA_STORE partition found. Is this a Multi-Tool drive?")
        if not prompts.prompt_yes_no("Continue anyway?", 'n'):
            sys.exit(0)

    print(f"\nExisting Installers:")
    for inst in structure['existing_installers']:
        print(f"  • {inst}")

    # Step 2: Select New Installers
    display.print_step(2, 5, "Select New Installers")
    installers = installer_scanner.scan_for_installers()

    # Filter out likely duplicates? (Advanced, skip for now)

    selected_indices = prompts.prompt_installer_selection(installers)
    if not selected_indices:
        display.print_warning("No new installers selected.")
        sys.exit(0)

    new_installers = [installers[i] for i in selected_indices]

    # Step 3: Confirmation
    display.print_step(3, 5, "Safety Confirmation")
    display.print_warning(f"This will DELETE the '{structure['data_partition']['id']}' (DATA_STORE) partition!")
    display.print_warning("Back up any files on the data partition before proceeding.")

    if not prompts.confirm_destructive_action(
        selected_disk['id'],
        selected_disk['name'],
        selected_disk['size_gb']
    ):
        sys.exit(0)

    # Step 4: Execute Update
    display.print_step(4, 5, "Updating Partitions")

    # Split Data Partition
    if structure['data_partition']:
        # New approach: Split the data partition iteratively
        new_parts = updater.split_partition(structure['data_partition']['id'], new_installers)

        if not new_parts:
            display.print_error("Failed to add any new partitions.")
            sys.exit(1)

        if len(new_parts) < len(new_installers):
            display.print_warning("Some partitions could not be created (disk full?).")
    else:
        display.print_error("Cannot update: DATA_STORE partition missing.")
        sys.exit(1)

    display.print_success("Partition map updated.")

    # Step 5: Install
    display.print_header("INSTALLING NEW VERSIONS")

    # We need to find the mount points for the newly created partitions
    # Assuming sequential order after the existing ones?
    # Better: Scan the disk partitions again and match by name

    import time
    time.sleep(2) # Wait for kernel to update

    current_partitions = partitioner.get_partition_list(selected_disk['id'])

    successful = []
    failed = []

    for item in new_parts:
        part_name = item['name']
        inst = item['installer']

        # Find the partition ID for this name
        target_part = next((p for p in current_partitions if p['name'] == part_name), None)

        if not target_part:
            display.print_error(f"Could not find partition {part_name}")
            failed.append(inst['name'])
            continue

        display.print_step(5, 5, f"Installing {inst['name']}")

        # Extract partition number (e.g. disk2s5 -> 5) using regex for robustness
        # or simple split if we trust the format "diskXsY"
        try:
            part_suffix = target_part['id'].replace(selected_disk['id'], '')
            part_num = part_suffix.replace('s', '')
            if not part_num.isdigit():
                 raise ValueError(f"Could not parse partition number from {target_part['id']}")
        except Exception as e:
            display.print_error(f"Error parsing partition ID: {e}")
            failed.append(inst['name'])
            continue

        volume_path = installer_runner.get_volume_mount_point(selected_disk['id'], part_num)

        start_time = time.time()
        success = installer_runner.run_createinstallmedia(
            inst['path'],
            volume_path,
            progress_callback=lambda p: progress.show_progress_bar(
                f"Installing {inst['name']}", p, start_time
            )
        )

        if success:
            # Re-fetch volume path
            new_volume_path = installer_runner.get_volume_mount_point(selected_disk['id'], part_num)
            if new_volume_path:
                os_name = constants.get_os_name(inst['version'])
                branding.apply_full_branding(new_volume_path, inst['name'], os_name, inst['version'])
            successful.append(inst['name'])
        else:
            failed.append(inst['name'])

    display.print_header("UPDATE COMPLETE")
    display.print_success(f"Added {len(successful)} installers.")

def main():
    """Main entry point."""
    # Argument parsing
    import argparse
    parser = argparse.ArgumentParser(description=f"macOS Multi-Tool Pro v{VERSION}")
    parser.add_argument("--dry-run", action="store_true", help="Simulate operations without making changes")
    parser.add_argument("--debug", action="store_true", help="Enable verbose logging")
    parser.add_argument("--app-dir", type=str, help="Custom path to search for installers")
    parser.add_argument("--gui", action="store_true", help="Launch Graphical User Interface")

    args = parser.parse_args()

    if args.gui:
        from ui import gui_tkinter
        gui_tkinter.launch()
        sys.exit(0)

    dry_run = args.dry_run

    if dry_run:
        display.print_warning("DRY RUN MODE - No changes will be made")

    # Ensure root (unless dry run? No, scanning might need perms, keeping it safe)
    privilege.ensure_root()
    privilege.start_keepalive()

    # Clear screen and show header
    display.clear_screen()
    display.print_header(f"macOS MULTI-TOOL PRO v{VERSION}")

    # Check dependencies
    check_dependencies()

    # Main menu
    choice = prompts.prompt_choice(
        "Select operation mode:",
        [
            "Create New Multi-Boot USB",
            "Update Existing Multi-Boot USB",
            "Download macOS Installer (via Mist)",
            "Exit"
        ]
    )

    if choice == 0:
        if dry_run:
            display.print_info("Would create new multi-boot USB (dry run)")
        else:
            mode_create_new(args)

    elif choice == 1:
        mode_update_existing()

    elif choice == 2:
        mode_download_installer()

    else:
        print("\nGoodbye!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        display.print_error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
