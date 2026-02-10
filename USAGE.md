# Usage Guide - macOS Multi-Tool Pro

This comprehensive guide explains how to use **macOS Multi-Tool Pro** effectively, from preparation to booting.

## 🚀 Quick Start

1.  **Prepare Installers**: Ensure your "Install macOS..." apps are in `/Applications`.
2.  **Insert USB**: Plug in a USB drive (16GB+ recommended, 32GB+ for multiple installers).
3.  **Run Tool**:
    ```bash
    chmod +x main.py
    sudo ./main.py
    ```

---

## 📖 Command Reference

### Interactive Mode (Standard)
```bash
sudo ./main.py
```
This launches the interactive wizard. This is the recommended way to use the tool.

### Simulation Mode (Safe)
```bash
sudo ./main.py --dry-run
```
Runs the entire process **without making any changes** to your disk. Useful for testing which installers are detected and verifying the partition layout plan.

### Help
```bash
./main.py --help
```
Displays version information and basic command-line usage.

---

## 🌊 Complete Workflow

### Step 1: Installer Scanning
The tool automatically scans these locations for valid macOS installers:
- `/Applications`
- `/Applications/Utilities`
- `~/Downloads`
- `~/Desktop`

**What you will see:**
A list of detected installers with their version, size, and status.
- **FULL**: Ready to use.
- **STUB**: Incomplete installer (missing payload). The tool will flag these and prevent their use.

**Action:**
Select the installers you want to include on your USB drive using the toggle menu.
- Type numbers (e.g., `1`, `3`) to toggle selection.
- Type `a` for All, `n` for None.
- Type `d` when Done.

### Step 2: Disk Selection
The tool scans for **external, removable** drives. It automatically hides:
- Your internal boot drive.
- Virtual disk images.
- Network drives.

**Action:**
Choose the target USB drive from the numbered list.

### Step 3: Safety Confirmation
**⚠️ CRITICAL STEP**
The tool will display the details of the drive you are about to erase.

**Action:**
Type `ERASE` (all caps) to confirm you want to format the drive. Any other input will cancel the operation.

### Step 4: The Automated Process
Once confirmed, the tool performs these actions automatically:

1.  **Backup**: Saves the current partition table to `/tmp/multiboot_backups/`.
2.  **Icon Extraction**: Saves high-quality icons from the installer apps.
3.  **Partitioning**:
    - Creates an `EFI` partition.
    - Creates a partition for each selected macOS installer (sized perfectly).
    - Creates a `DATA_STORE` partition with any remaining space.
4.  **Installation**:
    - Runs Apple's `createinstallmedia` for each partition.
    - Shows a progress bar for each installation.
5.  **Branding**:
    - Replaces the generic volume icon with the official OS icon.
    - Renames and blesses the volume so it appears correctly in the boot picker.

### Step 5: Booting
When the tool displays "OPERATION COMPLETE":

1.  Eject the USB drive safely.
2.  Plug it into the target Mac.
3.  Turn on the Mac and immediately hold the **Option (⌥)** key.
4.  You will see the boot picker with your custom-labeled macOS installers (e.g., "macOS Sonoma", "macOS Ventura").
5.  Select the one you wish to install.

---

## ❓ Troubleshooting

### "Root privileges required"
You must run the script with `sudo`. The tool attempts to elevate privileges automatically, but it's best to run it explicitly as `sudo ./main.py`.

### "No macOS installers found!"
- Check that your installer apps are in `/Applications`.
- Ensure they are full installers, not updates.
- Use `mist-cli` or the App Store to download full installers.

### "Stub installer detected"
This means you have a small ~20MB wrapper application instead of the full 12GB+ installer.
- **Solution**: Delete the stub app and re-download the full version.

### "Partitioning failed"
- Ensure the USB drive is not being used by another application.
- Try formatting the drive as "Mac OS Extended (Journaled)" in Disk Utility first to clear any corrupted partition tables.

### "Installation failed"
- Check the logs at `/tmp/multiboot_logs/` for detailed error messages.
- Ensure your USB drive is healthy and has fast read/write speeds.
