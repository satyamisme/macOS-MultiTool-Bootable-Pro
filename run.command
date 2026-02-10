#!/bin/bash
# run.sh - Auto-setup and execution script for macOS Multi-Tool Pro

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}       macOS Multi-Tool Pro - Auto Setup & Run        ${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Check Python Version
echo -e "\n${YELLOW}[1/4] Checking Python environment...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    echo "Please install Python 3.8+ (included with macOS 12+ or via python.org)"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "Found Python ${PYTHON_VERSION}"

# 2. Check for Homebrew (Optional but recommended)
echo -e "\n${YELLOW}[2/4] Checking optional dependencies...${NC}"
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Warning: Homebrew is not installed.${NC}"
    echo "Homebrew is recommended for installing 'mist-cli' (installer downloader)."
    read -p "Do you want to install Homebrew now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo "Skipping Homebrew installation."
    fi
else
    echo -e "Homebrew is installed."

    # Check for mist-cli
    if ! command -v mist &> /dev/null; then
        echo -e "${YELLOW}mist-cli is missing.${NC}"
        read -p "Install mist-cli for downloading macOS installers? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            brew install mist
        fi
    else
        echo -e "mist-cli is installed."
    fi
fi

# 3. Setup Virtual Environment (Best Practice)
echo -e "\n${YELLOW}[3/4] Setting up Python virtual environment...${NC}"
VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install dev dependencies (if any needed for runtime, though mostly standard lib)
if [ -f "requirements.txt" ]; then
    echo "Installing/Updating dependencies..."
    pip install -q -r requirements.txt
fi

# 4. Run Application
echo -e "\n${YELLOW}[4/4] Launching application...${NC}"
echo -e "${GREEN}Requesting sudo privileges for disk operations...${NC}"

# We need to run python from the venv with sudo
# sudo preserves the environment or we call the venv python directly
sudo "$VENV_DIR/bin/python3" main.py "$@"

# Deactivate venv on exit
deactivate
