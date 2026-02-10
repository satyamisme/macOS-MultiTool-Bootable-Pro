"""
version_parser.py - Parse and compare macOS versions
ONE RESPONSIBILITY: Version string manipulation
"""

def parse_version(version_string):
    """
    Parse version string into comparable tuple.

    Args:
        version_string: Version like "14.6.1 Beta" or "15.2"

    Returns:
        tuple: (major, minor, patch) as integers
    """
    # Clean version string
    clean = version_string.split()[0].split('-')[0]

    try:
        parts = clean.split('.')
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return (major, minor, patch)
    except (IndexError, ValueError):
        return (0, 0, 0)

def compare_versions(version1, version2):
    """
    Compare two version strings.

    Returns:
        int: -1 if v1 < v2, 0 if equal, 1 if v1 > v2
    """
    v1_tuple = parse_version(version1)
    v2_tuple = parse_version(version2)

    if v1_tuple < v2_tuple:
        return -1
    elif v1_tuple > v2_tuple:
        return 1
    else:
        return 0

def is_update(current_version, new_version):
    """
    Check if new_version is an update to current_version.
    Same major version, but newer minor/patch.
    """
    current = parse_version(current_version)
    new = parse_version(new_version)

    # Must be same major version
    if current[0] != new[0]:
        return False

    # New version must be greater
    return new > current

def format_version_display(version_string):
    """Format version for display."""
    parsed = parse_version(version_string)
    if parsed[2] > 0:
        return f"{parsed[0]}.{parsed[1]}.{parsed[2]}"
    elif parsed[1] > 0:
        return f"{parsed[0]}.{parsed[1]}"
    else:
        return f"{parsed[0]}"
