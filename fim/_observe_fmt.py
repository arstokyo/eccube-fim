from datetime import datetime
from typing import Optional

from fim.utils import JST


def parse_usec(raw: str) -> Optional[datetime]:
    try:
        usec = int(raw)
        return datetime.fromtimestamp(usec / 1_000_000, tz=JST) if usec else None
    except (ValueError, OverflowError, OSError):
        return None


def fmt_rel(secs: int) -> str:
    if secs < 0:
        return "overdue"
    if secs < 60:
        return f"in {secs}s"
    m = secs // 60
    return f"in {m}m {secs % 60}s" if secs % 60 else f"in {m}m"


def fmt_age(secs: int) -> str:
    if secs < 60:
        return f"{secs}s ago"
    m = secs // 60
    return f"{m}m ago" if m < 60 else f"{m // 60}h ago"


def log_ts(line: str) -> Optional[float]:
    """Parse 'YYYY-MM-DD HH:MM:SS' prefix → Unix timestamp, or None."""
    if len(line) < 19:
        return None
    try:
        return datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST).timestamp()
    except ValueError:
        return None
