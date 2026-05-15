import logging
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from fim.config import Config
from fim.notify.email import EmailChannel
from fim.utils import JST

log = logging.getLogger(__name__)


def _print_targets_table(cfg: Config) -> bool:
    """Print per-file git tracking status. Return True if all files are tracked."""
    print(f"{'FILE':<60} {'GIT':<14}")
    print("-" * 74)
    all_ok = True
    for path in cfg.target_files:
        r = subprocess.run(
            ["git", "ls-files", "--error-unmatch", path],
            cwd=cfg.root_path, capture_output=True,
        )
        tracked = r.returncode == 0
        if not tracked:
            all_ok = False
        status = "tracked" if tracked else "NOT IN GIT"
        print(f"  {path:<58} {status:<14}")
    return all_ok


def _print_secrets_status(cfg: Config) -> None:
    pw_file = cfg.email.smtp_password_file
    pw_ok = bool(pw_file) and Path(pw_file).exists()
    print(f"Email recipients : {cfg.email.recipients or '(none)'}")
    print(f"SMTP password    : {'found' if pw_ok else 'NOT FOUND'} ({pw_file})")
    if cfg.slack.enabled:
        for wh_file in cfg.slack.webhook_url_files:
            wh_ok = Path(wh_file).exists()
            print(f"Slack webhook    : {'found' if wh_ok else 'NOT FOUND'} ({wh_file})")


def validate_config(cfg: Config) -> bool:
    """Print a validation report for all monitored files. Return True if all checks pass."""
    root = Path(cfg.root_path)
    print(f"root_path  : {cfg.root_path}  {'OK' if root.is_dir() else 'NOT FOUND'}")
    print(f"hostname   : {socket.gethostname()}")
    print()
    all_ok = _print_targets_table(cfg)
    print()
    _print_secrets_status(cfg)
    print()
    result = "PASSED" if all_ok else "FAILED — fix the issues above"
    print(f"Config validation {result}")
    return all_ok


def send_test_mail(cfg: Config) -> int:
    """Send a test email using the configured SMTP settings. Return 0 on success."""
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    print(f"Sending test email to {cfg.email.recipients} "
          f"via {cfg.email.smtp_host}:{cfg.email.smtp_port} ...")
    detection = {
        "path": "(test)",
        "full_path": "(test)",
        "root_path": cfg.root_path,
        "git_status": "",
        "diff": "(This is a test — no tampering was detected.)",
        "mtime": now,
        "sha256": "",
    }
    try:
        EmailChannel(cfg.email).send(socket.gethostname(), detection)
    except Exception as e:
        log.error("Test email failed: %s", e)
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    print("Test email sent successfully")
    return 0


def _show_diff_summary(cfg: Config, file_path: str, message: str) -> bool:
    """Print git diff and confirm details. Return False if no changes found."""
    r = subprocess.run(
        ["git", "diff", "HEAD", "--", file_path],
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
    subprocess.run(["git", "add", file_path], cwd=cfg.root_path, check=True)
    commit_msg = f"FIM-approved: {message}" if message else f"FIM-approved: {file_path}"
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=cfg.root_path, check=True)
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
