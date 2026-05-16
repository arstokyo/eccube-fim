import logging
import subprocess
from typing import Callable, Optional

from fim.config import Config
from fim.git import _safe_dir_flag

log = logging.getLogger(__name__)


def _show_diff_summary(cfg: Config, file_path: str, message: str) -> bool:
    """Print git diff and confirm details. Return False if no changes found."""
    r = subprocess.run(
        ["git", *_safe_dir_flag(cfg.root_path), "diff", "HEAD", "--", file_path],
        cwd=cfg.root_path, capture_output=True, text=True,
    )
    if not r.stdout.strip():
        print(f"No uncommitted changes in: {file_path}")
        return False
    print(r.stdout)
    print("-" * 60)
    print(f"File   : {file_path}")
    print(f"Reason : {message or '(none)'}")
    print("-" * 60)
    return True


def _git_commit_approved(cfg: Config, file_path: str, message: str) -> None:
    sd = _safe_dir_flag(cfg.root_path)
    subprocess.run(["git", *sd, "add", file_path], cwd=cfg.root_path, check=True)
    commit_msg = f"FIM-approved: {message}" if message else f"FIM-approved: {file_path}"
    subprocess.run(["git", *sd, "commit", "-m", commit_msg], cwd=cfg.root_path, check=True)
    log.info("Approved: %s (message: %s)", file_path, message or "(none)")


def approve_change(cfg: Config, file_path: str, message: str = "",
                   confirm_fn: Optional[Callable] = None) -> bool:
    """Stage and commit a file change as FIM-approved.

    confirm_fn is injectable for testing — defaults to stdin prompt.
    Returns True if committed, False if cancelled.
    """
    if not _show_diff_summary(cfg, file_path, message):
        return False

    def _default_confirm() -> str:
        return input("Commit this change as FIM-approved? [y/N]: ").strip().lower()

    if (confirm_fn or _default_confirm)() != "y":
        print("Cancelled")
        return False
    _git_commit_approved(cfg, file_path, message)
    print("Committed. Alerts for this change will stop at the next check cycle.")
    return True
