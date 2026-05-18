import getpass
import os
import sys

import yaml

from fim.config import load_config
from fim.exceptions import FimConfigError
from fim.validate import validate_config


def _require_tty() -> bool:
    if not sys.stdin.isatty():
        print(
            "setup-notify requires an interactive terminal.\n"
            "Alternative: run 'sudo bash install.sh --reconfigure'",
            file=sys.stderr,
        )
        return False
    return True


def _prompt(label: str, default: str = "", secret: bool = False) -> str:
    display = f"{label} [{default}]: " if default else f"{label}: "
    if secret:
        return getpass.getpass(display) or default
    return input(display).strip() or default


def _ask_yes_no(question: str, default_yes: bool = False) -> bool:
    hint = "[Y/n]" if default_yes else "[y/N]"
    answer = input(f"{question} {hint}: ").strip().lower()
    if not answer:
        return default_yes
    return answer == "y"


def _secure_write(path: str, content: str) -> None:
    # os.open sets mode 0600 before any bytes land on disk — no TOCTOU window
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    try:
        os.chown(path, 0, 0)
    except OSError:
        pass  # not running as root in tests; mode 0600 is already applied


def _collect_email(config_dir: str) -> dict[str, object]:
    print("\n=== Email credentials ===")
    smtp_host = _prompt("SMTP host")
    smtp_port = _prompt("SMTP port", "587")
    smtp_user = _prompt("SMTP user")
    smtp_password = _prompt("SMTP password", secret=True)
    from_addr = _prompt("From address", smtp_user)
    rcpt_raw = _prompt("Recipients (comma-separated)")

    if not smtp_host:
        raise ValueError("SMTP host is required")
    if not smtp_port.isdigit():
        raise ValueError("SMTP port must be a number")
    recipients = [r.strip() for r in rcpt_raw.split(",") if r.strip()]
    if not recipients:
        raise ValueError("At least one recipient is required")

    password_file = os.path.join(config_dir, "smtp.password")
    _secure_write(password_file, smtp_password)
    print(f"Written {password_file} (chmod 600)")

    return {
        "enabled": True,
        "smtp_host": smtp_host,
        "smtp_port": int(smtp_port),
        "smtp_user": smtp_user,
        "smtp_password_file": password_file,
        "from": from_addr,
        "recipients": recipients,
    }


def _collect_slack(config_dir: str) -> dict[str, object]:
    print("\n=== Slack webhooks ===")
    webhook_files = []
    i = 1
    while True:
        wh = _prompt(f"Slack webhook URL {i} (empty to stop)")
        if not wh:
            break
        wh_file = os.path.join(config_dir, f"slack-{i}.webhook")
        _secure_write(wh_file, wh)
        print(f"Written {wh_file} (chmod 600)")
        webhook_files.append(wh_file)
        i += 1
    return {"enabled": bool(webhook_files), "webhook_url_files": webhook_files}


def _load_raw_notify(notify_path: str) -> dict[str, object]:
    if not os.path.exists(notify_path):
        return {"email": {"enabled": False}, "slack": {"enabled": False}}
    with open(notify_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _print_notify_status(data: dict[str, object]) -> None:
    email_on = data.get("email", {}).get("enabled", False)
    slack_on = data.get("slack", {}).get("enabled", False)
    print("\nCurrent status:")
    print(f"  email : {'enabled' if email_on else 'disabled'}")
    print(f"  slack : {'enabled' if slack_on else 'disabled'}")


def _apply_and_validate(config_dir: str, data: dict[str, object], notify_path: str) -> int:
    _secure_write(notify_path, yaml.dump(data, allow_unicode=True, default_flow_style=False))
    print(f"\nWritten {notify_path}")
    try:
        cfg = load_config(config_dir)
    except FimConfigError as e:
        print(f"Config error — fix before next check:\n  {e}", file=sys.stderr)
        return 1
    print()
    return 0 if validate_config(cfg) else 1


def setup_notify_interactive(config_dir: str) -> int:
    """Interactive wizard to configure email and Slack notification channels."""
    if not _require_tty():
        return 1
    notify_path = os.path.join(config_dir, "notify.yaml")
    data = _load_raw_notify(notify_path)
    _print_notify_status(data)
    try:
        if _ask_yes_no("\nConfigure email?"):
            data["email"] = _collect_email(config_dir)
        else:
            print("Email unchanged.")
        if _ask_yes_no("Configure Slack?"):
            data["slack"] = _collect_slack(config_dir)
        else:
            print("Slack unchanged.")
    except (ValueError, KeyboardInterrupt) as e:
        print(f"\nAborted: {e}", file=sys.stderr)
        return 1
    return _apply_and_validate(config_dir, data, notify_path)
