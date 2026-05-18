import subprocess
from datetime import datetime
from pathlib import Path

from fim.exceptions import FimGitError
from fim.utils import JST

_GIT_STATUS_TIMEOUT = 60
_GIT_DIFF_TIMEOUT   = 30
_GIT_DIFF_MAX_LINES = 50


def _safe_dir_flag(root_path: str) -> list:
    # per-invocation override; avoids writing to /etc/gitconfig system-wide
    return ["-c", f"safe.directory={root_path}"]


def git_status(root_path: str) -> dict[str, str]:
    """Return porcelain status map {relative_path: xy_code} for the repo."""
    r = subprocess.run(
        ["git", *_safe_dir_flag(root_path), "status", "--porcelain"],
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
        ["git", *_safe_dir_flag(root_path), "diff", "HEAD", "--", filepath],
        cwd=root_path, capture_output=True, text=True, timeout=_GIT_DIFF_TIMEOUT,
    )
    if r.returncode != 0:
        raise FimGitError(f"git diff failed: {r.stderr.strip()}")
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


def is_git_tracked(root_path: str, file_path: str) -> bool:
    """Return True if file_path is tracked in the git repo at root_path.

    Returns False for both "not tracked" and git-unreachable conditions.
    """
    try:
        r = subprocess.run(
            ["git", *_safe_dir_flag(root_path),
             "ls-files", "--error-unmatch", file_path],
            cwd=root_path, capture_output=True,
        )
        return r.returncode == 0
    except OSError:
        return False
