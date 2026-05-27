import hashlib
import os
import subprocess
import sys
from pathlib import Path

_EDITOR_FALLBACK = "vi"


def file_hash(path: str) -> str:
    """Return sha256 hex digest of file contents; empty string if file is missing."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""


def open_in_editor(path: str) -> bool:
    """Open `path` in $EDITOR (or vi). Blocks until the editor exits.

    Return True if the editor ran, False if the executable was not found.
    """
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or _EDITOR_FALLBACK
    try:
        subprocess.run([editor, path])
        return True
    except FileNotFoundError:
        print(f"Editor not found: {editor!r} — set $EDITOR to a valid executable.",
              file=sys.stderr)
        return False
