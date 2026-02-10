"""
progress.py - Progress bar and spinner utilities
ONE RESPONSIBILITY: Show operation progress
ZERO BUGS: Safe terminal output with fallback
"""

import sys
import time

def show_progress_bar(label, percent, start_time=None, width=40):
    """
    Display progress bar with optional ETA.

    Args:
        label: Operation label
        percent: Progress percentage (0-100)
        start_time: Start timestamp for ETA calculation
        width: Bar width in characters
    """
    # Clamp percent
    percent = max(0, min(100, percent))

    # Calculate filled portion
    filled = int(width * percent / 100)

    # Build bar
    try:
        bar = "█" * filled + "░" * (width - filled)
    except UnicodeEncodeError:
        # Fallback for terminals without Unicode
        bar = "#" * filled + "-" * (width - filled)

    # Calculate ETA
    eta_str = ""
    if start_time and percent > 5:  # Wait for 5% before showing ETA
        elapsed = time.time() - start_time
        if percent > 0:
            total_estimated = (elapsed / percent) * 100
            remaining = total_estimated - elapsed

            # Format ETA
            if remaining < 60:
                eta_str = f" | ETA: {int(remaining)}s"
            else:
                minutes = int(remaining / 60)
                seconds = int(remaining % 60)
                eta_str = f" | ETA: {minutes}m {seconds}s"

    # Output
    output = f"\r{label}: [{bar}] {percent:3d}%{eta_str}"
    sys.stdout.write(output)
    sys.stdout.flush()

    # Newline when complete
    if percent >= 100:
        print()

class Spinner:
    """Simple text spinner for indefinite operations."""

    def __init__(self, message="Working"):
        self.message = message
        self.frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.current = 0
        self.running = False

    def start(self):
        """Start spinner."""
        self.running = True
        self._spin()

    def stop(self, final_message=None):
        """Stop spinner and optionally show final message."""
        self.running = False
        sys.stdout.write('\r' + ' ' * 80 + '\r')  # Clear line
        if final_message:
            print(final_message)
        sys.stdout.flush()

    def _spin(self):
        """Internal spin method."""
        if not self.running:
            return

        frame = self.frames[self.current % len(self.frames)]
        sys.stdout.write(f'\r{frame} {self.message}...')
        sys.stdout.flush()
        self.current += 1

def show_step_progress(current, total, description):
    """
    Show step progress (e.g., "Step 3/5: Installing Sonoma").

    Args:
        current: Current step number
        total: Total steps
        description: Step description
    """
    from ui.display import Colors

    percent = int((current / total) * 100)
    bar_width = 20
    filled = int(bar_width * current / total)
    bar = "█" * filled + "░" * (bar_width - filled)

    print(f"\n{Colors.BOLD}[{current}/{total}] {description}{Colors.END}")
    print(f"Progress: [{bar}] {percent}%")
