import os
import sys


def require_root() -> bool:
    """Return True if running as root; print an error and return False otherwise."""
    if os.geteuid() == 0:
        return True
    print("Error: must be run as root", file=sys.stderr)
    return False
