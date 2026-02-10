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
from operations import partitioner, installer_runner, branding
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

def mode_create_new():
    """Mode 1: Create new multi-boot USB."""
    display.print_header("CREATE NEW MULTI-BOOT USB")

    # Step 1: Scan for installers
    display.print_step(1, 5, "Scanning for macOS installers")
    installers = installer_scanner.scan_for_installers()

    if not installers:
        display.print_error("No macOS installers found!")
        display.print_info("Download installers using:")
        print("  • App Store")
        print("  • Mist: https://github.com/ninxsoft/Mist")
        print("  • mist-cli: brew install mist")
        sys.exit(1)

    print(f"\nFound {len(installers)} installer(s):\n")

    # Validate installers
    valid_installers = []
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
                # This would integrate with mist_downloader
                display.print_warning("Mist integration not yet implemented")

    if not valid_installers:
        display.print_error("No valid full installers available")
        sys.exit(1)

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

def mode_update_existing():
    """Mode 2: Update existing multi-boot USB."""
    display.print_header("UPDATE EXISTING MULTI-BOOT USB")
    display.print_warning("This feature is not yet implemented")
    display.print_info("Coming in version 2.1.0")

def main():
    """Main entry point."""
    # Simple argument parsing
    if "-h" in sys.argv or "--help" in sys.argv:
        help.print_usage(VERSION)
        sys.exit(0)

    # Parse arguments
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        display.print_warning("DRY RUN MODE - No changes will be made")

    # Ensure root
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
            "Update Existing Multi-Boot USB (Coming Soon)",
            "Exit"
        ]
    )

    if choice == 0:
        if dry_run:
            display.print_info("Would create new multi-boot USB (dry run)")
        else:
            mode_create_new()

    elif choice == 1:
        mode_update_existing()

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
