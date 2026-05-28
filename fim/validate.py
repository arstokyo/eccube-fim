import logging
import socket
import sys
from pathlib import Path

from common.notify_config import print_secrets_status as _print_secrets_status
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


def validate_config(cfg: Config) -> bool:
    """Print a validation report for all monitored files. Return True if all checks pass."""
    root = Path(cfg.root_path)
    print(f"root_path  : {cfg.root_path}  {'OK' if root.is_dir() else 'NOT FOUND'}")
    print(f"hostname   : {socket.gethostname()}")
    print()
    all_ok = _print_targets_table(cfg)
    print()
    _print_secrets_status(cfg.email, cfg.slack)
    print()
    result = "PASSED" if all_ok else "FAILED — fix the issues above"
    print(f"Config validation {result}")
    return all_ok


def send_test_mail(cfg: Config) -> int:
    # known: near-duplicate of malware/validate.send_test_mail — dispatch path differs;
    # FIM uses send_test_notification() which builds a Detection; malware builds RenderedNotification directly
    """Send a test email using the configured SMTP settings. Return 0 on success."""
    if not cfg.email.enabled:
        print("Email is disabled in notify.yaml — nothing to test.", file=sys.stderr)
        return 1
    print(f"Sending test email to {cfg.email.recipients} "
          f"via {cfg.email.smtp_host}:{cfg.email.smtp_port} ...")
    try:
        results = send_test_notification(cfg, socket.gethostname(), channel_name="email")
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
    # known: near-duplicate of malware/validate.send_test_slack — same dispatch difference as send_test_mail
    """Send a test Slack message using the configured webhook. Return 0 on success."""
    if not cfg.slack.enabled:
        print("Slack is disabled in notify.yaml — nothing to test.", file=sys.stderr)
        return 1
    n = len(cfg.slack.webhook_url_files)
    print(f"Sending test Slack message via {n} webhook(s) ...")
    try:
        results = send_test_notification(cfg, socket.gethostname(), channel_name="slack")
    except Exception as e:
        log.error("Test Slack failed: %s", e)
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    if not results.get("SlackChannel", False):
        print("FAILED: Slack send failed", file=sys.stderr)
        return 1
    print("Test Slack message sent successfully")
    return 0
