# Error Handling and Recovery Guide

This document details how **macOS Multi-Tool Pro** handles errors, how to troubleshoot common issues, and procedures for recovering from failed operations.

## 📝 Error Logging

All operations are logged to:
`/tmp/multiboot_logs/multiboot_YYYYMMDD_HHMMSS.log`

If you encounter an issue, please check this file first. It contains detailed stack traces and command outputs that are not shown in the terminal.

---

## 🛑 Common Error Scenarios

### 1. "Root privileges required"
**Cause:** The script was run without `sudo`.
**Resolution:**
```bash
sudo ./main.py
```

### 2. "No macOS installers found"
**Cause:**
- Installers are not in `/Applications`.
- Only "stub" installers (20MB) are present, not full installers (12GB+).
**Resolution:**
- Download full installers using `mist-cli` or the App Store.
- Move installers to `/Applications`.

### 3. "Partitioning failed"
**Cause:**
- The USB drive is mounted or busy.
- The partition table is corrupted.
- Another process (like Spotlight) is accessing the drive.
**Resolution:**
1. Unmount the drive manually: `diskutil unmountDisk force /dev/diskX`
2. Format the drive as "Mac OS Extended (Journaled)" in Disk Utility to clear the table.
3. Retry the operation.

### 4. "Installation failed" (createinstallmedia error)
**Cause:**
- The installer file is corrupted.
- The USB drive has bad sectors or is too slow.
- The target volume name is invalid.
**Resolution:**
- Check the checksum of your installer app.
- Try a different USB drive.
- Ensure you have enough free space on your system drive (for temporary files).

---

## 🚑 Recovery Procedures

### Scenario A: USB Drive is Unreadable/Corrupted
If the tool fails mid-partitioning, your USB drive might not mount.

**Recovery Steps:**
1. Open **Disk Utility**.
2. Select the **physical device** (not the volume) in the sidebar.
   - *View -> Show All Devices* might be needed.
3. Click **Erase**.
4. Choose:
   - **Name**: UNTITLED
   - **Format**: Mac OS Extended (Journaled)
   - **Scheme**: GUID Partition Map
5. Click **Erase**.

### Scenario B: Accidental Partition Table Damage
If you suspect the wrong disk was targeted (despite safety checks), check the backup.

**Recovery Steps:**
1. Navigate to `/tmp/multiboot_backups/`.
2. Find the file matching your disk ID and timestamp (e.g., `partition_table_disk2_1700000000.txt`).
3. This file contains the *original* partition layout. You can use it as a reference to manually recreate partitions using `diskutil`.
   *Note: This does not restore data, only the layout structure.*

---

## 🔍 Exit Codes

| Code | Meaning |
|------|---------|
| `0`  | Success |
| `1`  | General Error (Missing tools, invalid input, permission denied) |
| `130`| Interrupted by User (Ctrl+C) |

---

## 🐛 Reporting Bugs

If you find a bug not listed here, please open an issue on GitHub with:
1. The log file content.
2. The exact command you ran.
3. Your macOS version and Python version.
