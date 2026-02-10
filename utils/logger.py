"""
logger.py - Logging system for debugging
ONE RESPONSIBILITY: Log operations
"""

import logging
import os
from datetime import datetime

LOG_DIR = "/tmp/multiboot_logs"
LOG_FILE = None

def setup_logging(verbose=False):
    """Initialize logging system."""
    global LOG_FILE

    # Create log directory
    os.makedirs(LOG_DIR, exist_ok=True)

    # Generate log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_FILE = os.path.join(LOG_DIR, f"multiboot_{timestamp}.log")

    # Configure logging
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler() if verbose else logging.NullHandler()
        ]
    )

    logging.info(f"Logging started - {timestamp}")
    return LOG_FILE

def log_info(message):
    """Log info message."""
    logging.info(message)

def log_error(message):
    """Log error message."""
    logging.error(message)

def log_warning(message):
    """Log warning message."""
    logging.warning(message)

def get_log_file():
    """Get current log file path."""
    return LOG_FILE
