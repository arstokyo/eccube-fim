import logging
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

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
        try:
            r = subprocess.run(
                ["git", "ls-files", "--error-unmatch", path],
                cwd=cfg.root_path, capture_output=True,
            )
            tracked = r.returncode == 0
        except OSError:
            # root_path does not exist or is not accessible
            tracked = False
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
        ok = EmailChannel(cfg.email).send(socket.gethostname(), detection)
        if not ok:
            print("FAILED: email send failed", file=sys.stderr)
            return 1
    except Exception as e:
        log.error("Test email failed: %s", e)
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    print("Test email sent successfully")
    return 0
