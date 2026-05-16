import json
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

__version__ = "1.0.0"
REPO_SLUG         = "arstokyo/eccube-fim"
VERSION_CHECK_URL = f"https://api.github.com/repos/{REPO_SLUG}/releases/latest"
# /run is tmpfs on systemd; stamp disappears after reboot — forces a fresh check after restart
VERSION_CHECK_STAMP = "/var/run/eccube-fim/version_check"

_CHECK_INTERVAL_HOURS = 24
_FETCH_TIMEOUT        = 5


def warn_if_update(stamp_path: Optional[str] = None) -> None:
    """Print a one-line warning if a newer release is available.

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
        print(f"[FIM] New version {latest} available (current: {current}). Run: sudo bash install.sh")


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


def _fetch_latest() -> Optional[tuple]:
    try:
        req = urllib.request.Request(VERSION_CHECK_URL, headers={"User-Agent": "eccube-fim"})
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read())
        latest = data.get("tag_name", "").lstrip("v")
        if latest and latest != __version__:
            return (__version__, latest)
    except Exception:
        pass  # silent on network error, timeout, JSON parse failure
    return None
