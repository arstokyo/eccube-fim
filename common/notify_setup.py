import sys
from pathlib import Path

import yaml

from common.constants import DEFAULT_CONFIG_DIR


def setup_notify_interactive(config_dir: str) -> int:
    """Prompt the user to configure email / Slack in notify.yaml.

    Return 0 on success, 1 on error.
    """
    notify_path = Path(config_dir) / "notify.yaml"
    try:
        existing: dict = yaml.safe_load(notify_path.read_text(encoding="utf-8")) or {}
    except OSError:
        existing = {}

    print("=== Notification setup wizard ===")
    result: dict = {}
    result["email"] = _prompt_email(existing.get("email") or {})
    result["slack"] = _prompt_slack(existing.get("slack") or {})

    try:
        notify_path.write_text(yaml.dump(result, allow_unicode=True, sort_keys=False),
                               encoding="utf-8")
        print(f"Saved: {notify_path}")
    except OSError as e:
        print(f"Error writing {notify_path}: {e}", file=sys.stderr)
        return 1
    return 0


def _prompt_email(current: dict) -> dict:
    enabled = _yes_no("Enable email notifications?", current.get("enabled", False))
    if not enabled:
        return {"enabled": False}
    # Key names must match notify.yaml structure consumed by _parse() in both config modules
    # STARTTLS is always enforced by EmailChannel — no use_tls toggle exposed here
    return {
        "enabled":            True,
        "smtp_host":          _ask("SMTP host", current.get("smtp_host", "")),
        "smtp_port":          _safe_int(_ask("SMTP port", str(current.get("smtp_port", 587))), 587),
        "smtp_user":          _ask("SMTP user (blank = no auth)", current.get("smtp_user", "")),
        "smtp_password_file": _ask("SMTP password file",
                                   current.get("smtp_password_file",
                                               f"{DEFAULT_CONFIG_DIR}/smtp.password")),
        "from":               _ask("From address", current.get("from", "")),
        "recipients":         [_ask("To address",
                                    (current.get("recipients") or [""])[0])],
    }


def _prompt_slack(current: dict) -> dict:
    enabled = _yes_no("Enable Slack notifications?", current.get("enabled", False))
    if not enabled:
        return {"enabled": False}
    existing_files = current.get("webhook_url_files") or [f"{DEFAULT_CONFIG_DIR}/slack.webhook"]
    return {
        "enabled":           True,
        "webhook_url_files": [_ask("Webhook URL file path", existing_files[0])],
    }


def _safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except ValueError:
        print(f"  Invalid value {value!r} — using {default}", file=sys.stderr)
        return default


def _ask(prompt: str, default: str) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"  {prompt}{suffix}: ").strip()
    return value or default


def _yes_no(prompt: str, default: bool) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    ans = input(f"  {prompt} {suffix}: ").strip().lower()
    if not ans:
        return default
    return ans.startswith("y")
