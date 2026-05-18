import logging
import socket
import sys
from pathlib import Path

from fim.config import Config
from fim.git import is_git_tracked
from fim.notify import send_test_notification

log = logging.getLogger(__name__)


def _print_targets_table(cfg: Config) -> bool:
    """Print per-file git tracking status. Return True if all files are tracked."""
    print(f"{'FILE':<60} {'GIT':<14}")
    print("-" * 74)
    all_ok = True
    for path in cfg.target_files:
        tracked = is_git_tracked(cfg.root_path, path)
        if not tracked:
            all_ok = False
        status = "tracked" if tracked else "NOT IN GIT"
        print(f"  {path:<58} {status:<14}")
    return all_ok


def _print_secrets_status(cfg: Config) -> None:
    if cfg.email.enabled:
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
    if not cfg.email.enabled:
        print("Email is disabled in notify.yaml — nothing to test.", file=sys.stderr)
        return 1
    print(f"Sending test email to {cfg.email.recipients} "
          f"via {cfg.email.smtp_host}:{cfg.email.smtp_port} ...")
    try:
        results = send_test_notification(cfg, socket.gethostname())
    except Exception as e:
        log.error("Test email failed: %s", e)
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    if not results.get("EmailChannel", False):
        print("FAILED: email send failed", file=sys.stderr)
        return 1
    print("Test email sent successfully")
    return 0


def send_test_slack(cfg: Config) -> int:
    """Send a test Slack message using the configured webhook. Return 0 on success."""
    if not cfg.slack.enabled:
        print("Slack is disabled in notify.yaml — nothing to test.", file=sys.stderr)
        return 1
    n = len(cfg.slack.webhook_url_files)
    print(f"Sending test Slack message via {n} webhook(s) ...")
    try:
        results = send_test_notification(cfg, socket.gethostname())
    except Exception as e:
        log.error("Test Slack failed: %s", e)
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    if not results.get("SlackChannel", False):
        print("FAILED: Slack send failed", file=sys.stderr)
        return 1
    print("Test Slack message sent successfully")
    return 0
