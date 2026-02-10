# Example Terminal Output

This document showcases the typical terminal output of **macOS Multi-Tool Pro**.

## 🚀 Successful Run

```bash
sudo ./main.py
```

```
======================================================================
                     macOS MULTI-TOOL PRO v2.0.0
======================================================================

[1/5] Scanning for macOS installers
Found 2 installer(s):

  • Install macOS Sonoma.app
    Version: 14.6.1 | Size: 13.52 GB | Status: FULL
  • Install macOS Ventura.app
    Version: 13.6.8 | Size: 12.87 GB | Status: FULL

Use number to toggle, 'a' for all, 'n' for none, 'd' when done:

============================================================
  [✓] 1. Install macOS Sonoma.app (14.6.1)
  [✓] 2. Install macOS Ventura.app (13.6.8)
============================================================

Selected: 2/2

[2/5] Detecting USB drives
Found 1 USB drive(s):

  • SanDisk Ultra (disk2) - 64.0 GB - USB

Select USB drive:
  [1] SanDisk Ultra (disk2) - 64.0 GB - USB

Your choice [1-1]: 1

[3/5] Confirmation

============================================================
⚠️  CRITICAL WARNING - DATA WILL BE DESTROYED ⚠️
============================================================

About to ERASE ALL DATA on:
  Disk ID:   /dev/disk2
  Name:      SanDisk Ultra
  Size:      64.00 GB

THIS ACTION CANNOT BE UNDONE!
ALL DATA ON THIS DISK WILL BE PERMANENTLY LOST!

Type 'ERASE' to confirm: ERASE
✓ Partition table backed up to: /tmp/multiboot_backups/partition_table_disk2_1707567890.txt

[4/5] Extracting installer icons
  Extracting icon from Install macOS Sonoma.app...
  Extracting icon from Install macOS Ventura.app...

[5/5] Creating partitions

Executing: sudo diskutil partitionDisk /dev/disk2 GPT... (2 partitions)
✓ Partitioning successful!

======================================================================
                     INSTALLING macOS TO PARTITIONS
======================================================================

[1/2] Installing Install macOS Sonoma.app 14.6.1
======================================================================

Running createinstallmedia...
  Installer: Install macOS Sonoma.app
  Target: /Volumes/INSTALL_Sonoma_14_6
Installing Install macOS Sonoma.app: [██████████████████████] 100% | ETA: 0s
  Applying branding...
  ✓ Branding applied successfully
✓ Install macOS Sonoma.app installed successfully!

======================================================================
[2/2] Installing Install macOS Ventura.app 13.6.8
======================================================================

Running createinstallmedia...
  Installer: Install macOS Ventura.app
  Target: /Volumes/INSTALL_Ventura_13_6
Installing Install macOS Ventura.app: [██████████████████████] 100% | ETA: 0s
  Applying branding...
  ✓ Branding applied successfully
✓ Install macOS Ventura.app installed successfully!

======================================================================
                        ✓ OPERATION COMPLETE
======================================================================
Successful installations: 2
✓ Install macOS Sonoma.app
✓ Install macOS Ventura.app

ℹ  Your multi-boot USB is ready!

To boot from this USB:
  1. Restart your Mac
  2. Hold Option (⌥) key during startup
  3. Select the desired macOS installer
======================================================================
```

## ❌ Failed Detection (Stub Installer)

```bash
sudo ./main.py
```

```
======================================================================
                     macOS MULTI-TOOL PRO v2.0.0
======================================================================

[1/5] Scanning for macOS installers
Found 1 installer(s):

  • Install macOS Sonoma.app
    Version: 14.6.1 | Size: 19.5 MB | Status: STUB
    Reason: SharedSupport.dmg missing

No valid full installers available
```

## ⚠️ Warning Simulation (Dry Run)

```bash
sudo ./main.py --dry-run
```

```
⚠️  DRY RUN MODE - No changes will be made

======================================================================
                     macOS MULTI-TOOL PRO v2.0.0
======================================================================

... (Scanning output similar to above) ...

[3/5] Confirmation
... (Standard confirmation prompt) ...

Type 'ERASE' to confirm: ERASE
✓ Partition table backed up to: /tmp/multiboot_backups/partition_table_disk2_1707567890.txt

ℹ  Would execute partition command (dry run):
   sudo diskutil partitionDisk /dev/disk2 GPT JHFS+ INSTALL_Sonoma_14 16G ...
```
