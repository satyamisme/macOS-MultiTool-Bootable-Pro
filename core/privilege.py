"""
privilege.py - Root privilege management
ONE RESPONSIBILITY: Ensure and maintain sudo access
"""

import os
import sys
import subprocess
import atexit
import signal

_sudo_process = None

def ensure_root():
    """Ensure script runs with root privileges."""
    if os.geteuid() != 0:
        print("\033[93m⚠️  Root privileges required. Elevating...\033[0m")
        os.execvp("sudo", ["sudo", sys.executable] + sys.argv)

def start_keepalive():
    """Start background process to keep sudo alive."""
    global _sudo_process

    # Validate sudo once
    result = subprocess.run(['sudo', '-v'], capture_output=True)
    if result.returncode != 0:
        print("❌ Failed to obtain sudo privileges")
        sys.exit(1)

    # Start keepalive process
    _sudo_process = subprocess.Popen(
        ['bash', '-c', 'while true; do sudo -n true; sleep 50; done'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setpgrp
    )

    # Register cleanup
    atexit.register(_cleanup)
    signal.signal(signal.SIGTERM, lambda s, f: _cleanup())
    signal.signal(signal.SIGINT, lambda s, f: _cleanup())

def _cleanup():
    """Clean up keepalive process."""
    global _sudo_process
    if _sudo_process:
        try:
            os.killpg(os.getpgid(_sudo_process.pid), signal.SIGTERM)
            _sudo_process.wait(timeout=2)
        except:
            try:
                os.killpg(os.getpgid(_sudo_process.pid), signal.SIGKILL)
            except:
                pass
        _sudo_process = None
