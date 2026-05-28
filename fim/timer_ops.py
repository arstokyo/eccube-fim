import re
import subprocess
import sys
from pathlib import Path

from common.constants import INSTALL_SYSTEMD_DIR
from fim.config import INSTALL_TIMER_NAME

TIMER_UNIT = str(Path(INSTALL_SYSTEMD_DIR) / INSTALL_TIMER_NAME)


def parse_interval_arg(value: str) -> int:
    """Parse '5', '30', '1h' into minutes (1–60). Raise ValueError on bad input."""
    value = value.strip().lower()
    m = re.fullmatch(r"(\d+)h", value)
    if m:
        hours = int(m.group(1))
        if hours != 1:
            raise ValueError("Only 1h is supported for hour intervals — use minutes (1–60) for other values")
        return 60
    m = re.fullmatch(r"(\d+)", value)
    if m:
        minutes = int(m.group(1))
        if minutes < 1:
            raise ValueError("Interval must be at least 1 minute")
        if minutes > 60:
            raise ValueError("Interval must be at most 60 minutes (use 1h for hourly)")
        return minutes
    raise ValueError(f"Invalid interval {value!r} — use a number of minutes (1–60) or '1h'")


def format_interval(minutes: int) -> str:
    if minutes >= 60 and minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes}m"


def get_timer_interval() -> int:
    """Read the current OnCalendar value from the installed timer unit.

    Return the interval in minutes. Raises OSError if the unit is not installed,
    ValueError if the OnCalendar line cannot be parsed.
    """
    text = Path(TIMER_UNIT).read_text(encoding="utf-8")
    m = re.search(r"OnCalendar=\*:0/(\d+)", text)
    if not m:
        raise ValueError(f"Cannot parse OnCalendar in {TIMER_UNIT}")
    return int(m.group(1))


def set_timer_interval(minutes: int) -> None:
    """Rewrite the OnCalendar line and reload + restart the timer unit.

    Raises OSError on file write failure; raises RuntimeError if systemctl fails.
    """
    text = Path(TIMER_UNIT).read_text(encoding="utf-8")
    new_text = re.sub(
        r"OnCalendar=\*:0/\d+",
        f"OnCalendar=*:0/{minutes}",
        text,
    )
    Path(TIMER_UNIT).write_text(new_text, encoding="utf-8")
    for cmd in [
        ["systemctl", "daemon-reload"],
        ["systemctl", "restart", "eccube-fim-check.timer"],
    ]:
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(
                f"{' '.join(cmd)} failed:\n{r.stderr.decode().strip()}"
            )


def show_timer() -> int:
    """Print the current timer interval. Return 0 on success, 1 on error."""
    try:
        minutes = get_timer_interval()
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(f"Check interval : {format_interval(minutes)}  ({minutes} minutes)")
    print(f"Timer unit     : {TIMER_UNIT}")
    return 0
