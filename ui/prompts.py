"""
prompts.py - User interaction prompts
ONE RESPONSIBILITY: Get user input safely
ZERO BUGS: Input validation and error handling
"""

import sys
from ui.display import Colors

def prompt_yes_no(question, default='n'):
    """
    Ask yes/no question.

    Args:
        question: Question text
        default: Default answer ('y' or 'n')

    Returns:
        bool: True for yes, False for no
    """
    suffix = "[Y/n]" if default == 'y' else "[y/N]"

    try:
        response = input(f"{question} {suffix}: ").strip().lower()

        if not response:
            return default == 'y'

        return response in ['y', 'yes']

    except (KeyboardInterrupt, EOFError):
        print()
        return False

def prompt_choice(question, options, allow_cancel=True):
    """
    Present multiple choice menu.

    Args:
        question: Question text
        options: List of option strings
        allow_cancel: Allow user to cancel (Ctrl+C)

    Returns:
        int: Selected option index (0-based), or None if cancelled
    """
    print(f"\n{question}")

    for i, option in enumerate(options, 1):
        print(f"  [{i}] {option}")

    if allow_cancel:
        print(f"\n  Press Ctrl+C to cancel")

    while True:
        try:
            response = input(f"\nYour choice [1-{len(options)}]: ").strip()

            if not response:
                continue

            choice = int(response)

            if 1 <= choice <= len(options):
                return choice - 1
            else:
                print(f"{Colors.RED}Please enter a number between 1 and {len(options)}{Colors.END}")

        except ValueError:
            print(f"{Colors.RED}Please enter a valid number{Colors.END}")

        except (KeyboardInterrupt, EOFError):
            if allow_cancel:
                print("\n")
                return None
            else:
                print(f"\n{Colors.YELLOW}Operation cannot be cancelled at this point{Colors.END}")

def prompt_text(question, default=None, validator=None):
    """
    Prompt for text input with optional validation.

    Args:
        question: Question text
        default: Default value
        validator: Optional function(text) -> (valid, error_msg)

    Returns:
        str: User input, or None if cancelled
    """
    suffix = f" [{default}]" if default else ""

    try:
        while True:
            response = input(f"{question}{suffix}: ").strip()

            if not response and default:
                return default

            if not response:
                print(f"{Colors.RED}Input required{Colors.END}")
                continue

            if validator:
                valid, error_msg = validator(response)
                if not valid:
                    print(f"{Colors.RED}{error_msg}{Colors.END}")
                    continue

            return response

    except (KeyboardInterrupt, EOFError):
        print()
        return None

def confirm_destructive_action(disk_id, disk_name, disk_size_gb):
    """
    Special confirmation for destructive operations.

    Returns:
        bool: True if user confirms
    """
    print(f"\n{Colors.RED}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.RED}{Colors.BOLD}⚠️  CRITICAL WARNING - DATA WILL BE DESTROYED ⚠️{Colors.END}")
    print(f"{Colors.RED}{Colors.BOLD}{'='*60}{Colors.END}\n")

    print(f"About to ERASE ALL DATA on:")
    print(f"  Disk ID:   {Colors.BOLD}/dev/{disk_id}{Colors.END}")
    print(f"  Name:      {Colors.BOLD}{disk_name}{Colors.END}")
    print(f"  Size:      {Colors.BOLD}{disk_size_gb:.2f} GB{Colors.END}")

    print(f"\n{Colors.RED}THIS ACTION CANNOT BE UNDONE!{Colors.END}")
    print(f"{Colors.RED}ALL DATA ON THIS DISK WILL BE PERMANENTLY LOST!{Colors.END}\n")

    try:
        confirmation = input(f"Type '{Colors.BOLD}ERASE{Colors.END}' to confirm: ").strip()
        return confirmation == "ERASE"

    except (KeyboardInterrupt, EOFError):
        print()
        return False

def prompt_installer_selection(installers):
    """
    Interactive installer selection with toggle.

    Args:
        installers: List of installer dicts

    Returns:
        list: Selected installer indices
    """
    if not installers:
        return []

    # All selected by default
    selected = [True] * len(installers)

    print("\nUse number to toggle, 'a' for all, 'n' for none, 'd' when done:")

    while True:
        # Display current selection
        print("\n" + "="*60)
        for i, inst in enumerate(installers):
            marker = "✓" if selected[i] else " "
            print(f"  [{marker}] {i+1}. {inst['name']} ({inst['version']})")
        print("="*60)

        # Show summary
        selected_count = sum(selected)
        print(f"\nSelected: {selected_count}/{len(installers)}")

        try:
            choice = input("\nToggle [1-9], 'a'll, 'n'one, or 'd'one: ").strip().lower()

            if choice == 'd':
                if selected_count == 0:
                    print(f"{Colors.YELLOW}No installers selected!{Colors.END}")
                    continue
                return [i for i, sel in enumerate(selected) if sel]

            elif choice == 'a':
                selected = [True] * len(installers)

            elif choice == 'n':
                selected = [False] * len(installers)

            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(installers):
                    selected[idx] = not selected[idx]
                else:
                    print(f"{Colors.RED}Invalid number{Colors.END}")

            else:
                print(f"{Colors.RED}Invalid input{Colors.END}")

        except (KeyboardInterrupt, EOFError):
            print()
            return []
