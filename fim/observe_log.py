import sys
from typing import Optional

from fim.utils import LOG_DIR

_LOG_PATH = LOG_DIR / "check.log"


def log_tail(lines: int, level: Optional[str]) -> int:
    """Print the last `lines` entries from check.log, optionally filtered by level.

    Return 0 on success, 1 if the log file is absent or unreadable.
    """
    try:
        with open(_LOG_PATH, encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except FileNotFoundError:
        print(f"Log file not found: {_LOG_PATH}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Cannot read log: {e}", file=sys.stderr)
        return 1
    if level:
        tag = f" {level.upper()} "
        all_lines = [ln for ln in all_lines if tag in ln]
    tail = all_lines[-lines:]
    for ln in tail:
        print(ln, end="")
    if not tail:
        label = f"{level.upper()} " if level else ""
        print(f"(no {label}log entries)")
    return 0
