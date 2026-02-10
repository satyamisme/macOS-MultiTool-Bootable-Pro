"""
display.py - Terminal display utilities
ONE RESPONSIBILITY: Formatted console output
ZERO BUGS: Safe color codes with fallback
"""

import sys

# ANSI color codes
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# Disable colors if not in TTY
if not sys.stdout.isatty():
    for attr in dir(Colors):
        if not attr.startswith('_'):
            setattr(Colors, attr, '')

def clear_screen():
    """Clear terminal screen."""
    import os
    os.system('clear' if os.name == 'posix' else 'cls')

def print_header(text, width=70):
    """Print styled header."""
    print(f"\n{Colors.BLUE}{'=' * width}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(width)}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * width}{Colors.END}\n")

def print_subheader(text):
    """Print styled subheader."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BLUE}{'-' * len(text)}{Colors.END}")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠  {text}{Colors.END}")

def print_info(text):
    """Print info message."""
    print(f"{Colors.CYAN}ℹ  {text}{Colors.END}")

def print_step(step_num, total_steps, description):
    """Print step indicator."""
    print(f"\n{Colors.BOLD}[{step_num}/{total_steps}] {description}{Colors.END}")

def print_table(headers, rows, col_widths=None):
    """
    Print formatted table.

    Args:
        headers: List of column headers
        rows: List of row data (each row is a list)
        col_widths: Optional list of column widths
    """
    if not rows:
        print("  (No data)")
        return

    # Auto-calculate widths if not provided
    if col_widths is None:
        col_widths = [len(str(h)) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_parts = []
    for i, header in enumerate(headers):
        width = col_widths[i] if i < len(col_widths) else 10
        header_parts.append(str(header).ljust(width))

    print("  " + " │ ".join(header_parts))

    # Print separator
    sep_parts = []
    for width in col_widths:
        sep_parts.append("─" * width)
    print("  " + "─┼─".join(sep_parts))

    # Print rows
    for row in rows:
        row_parts = []
        for i, cell in enumerate(row):
            width = col_widths[i] if i < len(col_widths) else 10
            row_parts.append(str(cell).ljust(width))
        print("  " + " │ ".join(row_parts))

def format_size(bytes_val):
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"

def format_time(seconds):
    """Format seconds into human-readable time."""
    if seconds < 0:
        return "calculating..."

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
