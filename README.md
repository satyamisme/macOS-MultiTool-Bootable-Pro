# macOS Multi-Tool Pro

**Version 2.0.0**

A modular, production-ready Python application for creating multi-boot macOS USB installers.

## 🚀 Features

- **Multi-Boot Support**: Create a single USB drive with multiple macOS installers (e.g., Sequoia, Sonoma, Ventura).
- **Smart Partitioning**: Automatically calculates partition sizes based on installer size + overhead buffer.
- **Safety First**:
  - Prevents accidental selection of boot disk or system volumes.
  - Requires explicit "ERASE" confirmation for destructive actions.
  - Automatically backs up partition tables before modifying disks.
- **Professional Branding**:
  - Extracts high-res icons from installers and applies them to the USB volumes.
  - Blesses volumes with proper boot labels (e.g., "macOS Sonoma 14.2").
- **Robust Detection**:
  - Scans for valid installers in standard locations.
  - Detects "stub" installers and prevents their use.
  - Filters strictly for external, removable USB drives.

## 📋 Requirements

- **macOS**: 10.13 High Sierra or later (Recommended: macOS 12+).
- **Python**: 3.8 or later (standard on macOS 12+).
- **Architecture**: Intel and Apple Silicon (M1/M2/M3) supported.
- **Privileges**: Root access (sudo) is required for disk operations.
- **Installers**: Full macOS installer applications (e.g., "Install macOS Sonoma.app") located in `/Applications`.

## 🧪 Testing

The repository includes a comprehensive verification suite to ensure your environment is ready.

To run the tests:
```bash
python3 tests/test_full_verification.py
```
This will check:
- Python version compatibility
- Required system commands (diskutil, sudo, du)
- Module imports and syntax

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/macOS-MultiTool-Pro.git
    cd macOS-MultiTool-Pro
    ```

2.  **Run the automated setup script**:
    ```bash
    chmod +x run.command
    ./run.command
    ```
    *Note: You can also double-click `run.command` in Finder to launch it.*

    This script will:
    - Check Python version.
    - Create a virtual environment to keep your system clean.
    - Install optional dependencies like `mist-cli`.
    - Launch the application with `sudo`.

## 🛠 Usage

1.  **Run the application (Recommended)**:
    ```bash
    ./run.command
    ```

2.  **Run Manually (Advanced)**:
    ```bash
    sudo ./main.py
    ```

3.  **Follow the interactive prompts**:
    - **Step 1**: The tool scans for available installers. Select which ones you want to include.
    - **Step 2**: Select the target USB drive from the list of safe, external options.
    - **Step 3**: Confirm the destructive operation by typing `ERASE`.
    - **Step 4**: Wait for the process to complete. The tool will:
        - Extract icons.
        - Partition the drive.
        - Install each selected macOS version.
        - Apply branding and boot labels.

3.  **Boot from your new USB**:
    - Restart your Mac.
    - Hold the **Option (⌥)** key during startup.
    - Select the desired macOS installer from the boot menu.

## ❓ Troubleshooting

Common issues and solutions:

- **"Root privileges required"**: Always run the script with `sudo`.
- **"No macOS installers found"**: Ensure you have downloaded the full installer (12GB+), not just an update stub. Use `mist-cli` to download full installers if needed.
- **"Partitioning failed"**: Unmount the USB drive first or format it as "Mac OS Extended (Journaled)" in Disk Utility to clear any corrupted partition tables.
- **"Installation failed"**: Check the logs at `/tmp/multiboot_logs/` for detailed error messages.

## 📂 Project Structure

```
macOS-MultiTool-Pro/
├── core/           # Constants and privilege management
├── detection/      # Scanner for installers and disks
├── safety/         # Boot guard and backup manager
├── operations/     # Partitioning and installer execution
├── integration/    # External tool integration (Mist)
├── ui/             # Terminal display and prompts
├── utils/          # Logging and helpers
└── main.py         # Main application entry point
```

## ⚠️ Disclaimer

**This tool involves destructive disk operations (formatting and partitioning).**
While extensive safety checks are in place, the authors are not responsible for any data loss. **Always double-check the target drive before confirming.**

## 📜 License

MIT License. See `LICENSE` for details.
