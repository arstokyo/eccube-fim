import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from fim.config import DEFAULT_CONFIG_DIR as _DEFAULT_CONFIG_DIR, VERSION_CHECK_STAMP

__version__ = "dev"
REPO_SLUG         = "arstokyo/eccube-fim"
VERSION_CHECK_URL = f"https://api.github.com/repos/{REPO_SLUG}/releases/latest"

_CHECK_INTERVAL_HOURS = 24
_FETCH_TIMEOUT        = 5


def read_installed_version(config_dir: str = _DEFAULT_CONFIG_DIR) -> str:
    """Return the installed version from the stamp file, or 'dev' if missing."""
    try:
        return (Path(config_dir) / ".version").read_text(encoding="utf-8").strip()
    except OSError:
        return "dev"


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
    current = read_installed_version()
    try:
        req = urllib.request.Request(VERSION_CHECK_URL,
                                     headers={"User-Agent": "eccube-fim"})
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read())
        tag = data.get("tag_name", "")
        latest = tag.lstrip("v")
        if not latest or latest == current:
            return None
        body = data.get("body", "")
        m = re.search(r'python_requires:\s*"(.*?)"', body)
        if m:
            requires = m.group(1)
            min_parts = tuple(int(x) for x in requires.lstrip(">=").split("."))
            if sys.version_info[:len(min_parts)] < min_parts:
                # latest release requires a newer Python — skip the warning
                return None
        return (current, latest)
    except Exception:
        pass  # known: intentionally silent — any error here would interrupt the user's primary command for a background check
    return None
