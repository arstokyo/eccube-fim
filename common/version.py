import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from common.constants import DEFAULT_CONFIG_DIR, FETCH_TIMEOUT as _FETCH_TIMEOUT

__version__        = "dev"
REPO_SLUG          = "arstokyo/eccube-fim"
VERSION_CHECK_URL  = f"https://api.github.com/repos/{REPO_SLUG}/releases/latest"

_CHECK_INTERVAL_HOURS = 24

_PYTHON_REQUIRES_RE = re.compile(r'python_requires:\s*"(.*?)"')


def parse_python_requires(body: str) -> str:
    """Extract the python_requires spec (e.g. '>=3.9') from a release body, or ''."""
    m = _PYTHON_REQUIRES_RE.search(body)
    return m.group(1) if m else ""


def python_meets(requires: str) -> bool:
    """Return True if the running interpreter satisfies a '>=X.Y' requirement.

    An empty requirement is treated as 'no constraint' and always passes.
    """
    if not requires:
        return True
    min_parts = tuple(int(x) for x in requires.lstrip(">=").split("."))
    return sys.version_info[:len(min_parts)] >= min_parts


def read_installed_version(config_dir: str = DEFAULT_CONFIG_DIR) -> str:
    """Return the installed version from the stamp file, or 'dev' if missing."""
    try:
        return (Path(config_dir) / ".version").read_text(encoding="utf-8").strip()
    except OSError:
        return "dev"


def warn_if_update(config_dir: str = DEFAULT_CONFIG_DIR,
                   stamp_path: Optional[str] = None) -> None:
    """Print a one-line warning if a newer release is available.

    Silent on any network or parse failure — never interrupts the primary command.
    """
    if stamp_path and _is_recent(stamp_path):
        return
    result = _fetch_latest(config_dir)
    if stamp_path:
        _touch_stamp(stamp_path)
    if result:
        current, latest = result
        print(f"[eccube-fim] New version {latest} available (current: {current}). "
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


def _fetch_latest(config_dir: str = DEFAULT_CONFIG_DIR) -> Optional[tuple[str, str]]:
    current = read_installed_version(config_dir)
    try:
        req = urllib.request.Request(VERSION_CHECK_URL,
                                     headers={"User-Agent": "eccube-fim"})
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read())
        tag = data.get("tag_name", "")
        latest = tag.lstrip("v")
        if not latest or latest == current:
            return None
        if not python_meets(parse_python_requires(data.get("body", ""))):
            return None
        return (current, latest)
    except Exception:
        pass  # known: intentionally silent on any network or parse failure
    return None
