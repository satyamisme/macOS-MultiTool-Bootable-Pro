"""
config.py - Configuration management
"""

class Config:
    def __init__(self):
        self.dry_run = False
        self.debug = False
        self.app_dir = None
        self.gui_mode = False

# Global instance for easy access if needed, but passing it is better
runtime_config = Config()
