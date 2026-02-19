from ui import display

def print_usage(version):
    """Print command-line usage information."""
    display.print_header(f"macOS MULTI-TOOL PRO v{version}")
    print("\nUSAGE:")
    print("  sudo ./main.py [OPTIONS]")
    print("\nOPTIONS:")
    print("  -h, --help       Show this help message and exit")
    print("  --dry-run        Simulate operations without making changes")
    print("  --debug          Enable verbose logging")
    print("  --app-dir PATH   Custom path to search for installers")
    print("  --gui            Launch Graphical User Interface")
    print("\nDESCRIPTION:")
    print("  macOS Multi-Tool Pro creates multi-boot USB installers for macOS.")
    print("  It scans for installers, partitions the drive, and installs multiple versions.")
    print("\nEXAMPLES:")
    print("  # Run normally (interactive mode)")
    print("  sudo ./main.py")
    print("\n  # Run in simulation mode")
    print("  sudo ./main.py --dry-run")
