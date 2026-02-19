# GUI Workflow Guide

This document describes the flow of the Graphical User Interface (GUI) for macOS Multi-Tool Pro.

## 🖥️ Main Window

The GUI is divided into three main sections:

### 1. Drive Selection (Top Left)
- **Dropdown**: Lists all connected, removable USB drives.
- **Refresh Button**: Re-scans for drives if you plugged one in after launching.
- **Details**: Shows the disk identifier (e.g., `disk2`) and size (e.g., `64.0 GB`).

### 2. Installer Selection (Top Right / Center)
- **List View**: Displays all detected macOS installers.
- **Columns**:
  - **Name**: e.g., "Install macOS Sonoma"
  - **Version**: e.g., "14.6.1"
  - **Size**: e.g., "13.52 GB"
  - **Status**:
    - `FULL`: Ready to install.
    - `STUB`: Incomplete (cannot be used).
    - `PARTIAL`: Download interrupted.
    - `DOWNLOADING`: Currently being downloaded by Mist.
- **Actions**:
  - **Select All**: Selects all valid FULL installers.
  - **Download New...**: Opens a dialog to download installers via Mist.

### 3. Execution & Logs (Bottom)
- **Create Button**: Starts the multi-boot creation process.
- **Log Window**: Displays real-time progress, commands being executed, and any errors.

---

## 🌊 Typical Workflow

1.  **Launch**: Run `./run.command --gui`.
2.  **Select Drive**: Pick your target USB drive from the dropdown.
3.  **Select OS**: Click on the macOS versions you want to include.
    - *Tip*: Hold `Cmd` or `Ctrl` to select multiple.
4.  **Download (Optional)**:
    - Click "Download New...".
    - Type "Sonoma" or "14".
    - Wait for the download to finish (status will update to `FULL`).
5.  **Create**:
    - Click "CREATE BOOTABLE USB".
    - Confirm the "ERASE" warning.
    - Watch the log window for progress.
6.  **Done**: When the log says "Success", eject your drive.
