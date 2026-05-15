import logging
import subprocess
from datetime import datetime
from pathlib import Path

from fim.exceptions import FimGitError
from fim.utils import JST

log = logging.getLogger(__name__)

_GIT_STATUS_TIMEOUT = 60
_GIT_DIFF_TIMEOUT   = 30
_GIT_DIFF_MAX_LINES = 50


def git_status(root_path: str) -> dict:
    """Return porcelain status map {relative_path: xy_code} for the repo."""
    r = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root_path, capture_output=True, text=True, timeout=_GIT_STATUS_TIMEOUT,
    )
    if r.returncode != 0:
        raise FimGitError(f"git status failed: {r.stderr.strip()}")
    out = {}
    for line in r.stdout.splitlines():
        if len(line) < 4:
            continue
        xy = line[:2].strip()
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ")[-1]
        out[path] = xy
    return out


def git_diff(root_path: str, filepath: str,
             max_lines: int = _GIT_DIFF_MAX_LINES) -> str:
    r = subprocess.run(
        ["git", "diff", "HEAD", "--", filepath],
        cwd=root_path, capture_output=True, text=True, timeout=_GIT_DIFF_TIMEOUT,
    )
    lines = r.stdout.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... ({len(lines) - max_lines} more lines omitted)"]
    return "\n".join(lines)


def file_mtime(root_path: str, filepath: str) -> str:
    try:
        mtime = (Path(root_path) / filepath).stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=JST).strftime("%Y-%m-%d %H:%M:%S JST")
    except OSError:
        return "(file not found)"
