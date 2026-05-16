import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

__version__ = "dev"
REPO_SLUG         = "arstokyo/eccube-fim"
VERSION_CHECK_URL = f"https://api.github.com/repos/{REPO_SLUG}/releases/latest"
# /run is tmpfs on systemd; stamp disappears after reboot — forces a fresh check after restart
VERSION_CHECK_STAMP = "/run/eccube-fim/version_check"

_CHECK_INTERVAL_HOURS = 24
_FETCH_TIMEOUT        = 5


def warn_if_update(stamp_path: Optional[str] = None) -> None:
    """Print a one-line warning if a newer compatible release is available.

    If stamp_path is given, skip the network call when a check was done
    within 24 hours. Always silent on network or parse failure.
    """
    if stamp_path and _is_recent(stamp_path):
        return
    result = _fetch_latest()
    if stamp_path:
        _touch_stamp(stamp_path)
    if result:
        current, latest = result
        print(f"[FIM] New version {latest} available (current: {current}). "
              f"Run: sudo eccube-fim upgrade")


def _is_recent(stamp_path: str) -> bool:
    try:
        age = (datetime.now().timestamp() - Path(stamp_path).stat().st_mtime) / 3600
        return age < _CHECK_INTERVAL_HOURS
    except OSError:
        return False


def _touch_stamp(stamp_path: str) -> None:
    try:
        p = Path(stamp_path)
        # /run is tmpfs on all systemd distros; dir disappears after reboot
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
    except OSError:
        pass


def _fetch_latest() -> Optional[tuple[str, str]]:
    """Return (current, latest) if a newer compatible release exists, else None.

    Returns None on network error, when already up-to-date, or when the
    latest release requires a newer Python than the running interpreter.
    """
    try:
        req = urllib.request.Request(VERSION_CHECK_URL,
                                     headers={"User-Agent": "eccube-fim"})
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read())
        tag = data.get("tag_name", "")
        latest = tag.lstrip("v")
        if not latest or latest == __version__:
            return None
        body = data.get("body", "")
        m = re.search(r'python_requires:\s*"(.*?)"', body)
        if m:
            requires = m.group(1)
            min_parts = tuple(int(x) for x in requires.lstrip(">=").split("."))
            if sys.version_info[:len(min_parts)] < min_parts:
                # latest release requires a newer Python — skip the warning
                return None
        return (__version__, latest)
    except Exception:
        pass  # silent on network error, timeout, JSON parse failure
    return None
