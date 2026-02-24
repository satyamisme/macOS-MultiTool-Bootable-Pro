"""
config_manager.py - Manage persistent user preferences
ONE RESPONSIBILITY: Load and save user settings to a JSON file
"""

import json
import os

CONFIG_FILE = os.path.expanduser("~/.macos_multitool_prefs.json")

DEFAULT_CONFIG = {
    "default_buffer": 2.0,
    "last_mode": "create", # "create" or "update"
    "window_width": 1000,
    "window_height": 850
}

def load_config():
    """Load configuration from file, falling back to defaults."""
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, 'r') as f:
            user_config = json.load(f)
            # Merge with defaults to ensure all keys exist
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
