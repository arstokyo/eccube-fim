from dataclasses import dataclass, field
from pathlib import Path

from common.constants import DEFAULT_SMTP_PORT
from common.exceptions import FimConfigError


@dataclass
class NotifyEmail:
    """SMTP notification channel configuration."""
    smtp_host: str = ""
    smtp_port: int = DEFAULT_SMTP_PORT
    smtp_user: str = ""
    smtp_password_file: str = ""
    from_addr: str = ""
    recipients: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class NotifySlack:
    """Slack notification channel configuration."""
    enabled: bool = False
    webhook_url_files: list[str] = field(default_factory=list)


def print_secrets_status(email: NotifyEmail, slack: NotifySlack) -> None:
    """Print whether the SMTP password file and Slack webhook files exist on disk."""
    if email.enabled:
        pw_ok = bool(email.smtp_password_file) and Path(email.smtp_password_file).exists()
        print(f"Email recipients : {email.recipients or '(none)'}")
        print(f"SMTP password    : {'found' if pw_ok else 'NOT FOUND'} ({email.smtp_password_file})")
    if slack.enabled:
        for wh_file in slack.webhook_url_files:
            wh_ok = Path(wh_file).exists()
            print(f"Slack webhook    : {'found' if wh_ok else 'NOT FOUND'} ({wh_file})")


def parse_notify_channels(notify: dict) -> tuple[NotifyEmail, NotifySlack]:
    """Build NotifyEmail and NotifySlack from a raw notify.yaml dict."""
    ec = notify.get("email", {})
    sc = notify.get("slack", {})
    return (
        NotifyEmail(
            smtp_host=ec.get("smtp_host", ""),
            smtp_port=ec.get("smtp_port", DEFAULT_SMTP_PORT),
            smtp_user=ec.get("smtp_user", ""),
            smtp_password_file=ec.get("smtp_password_file", ""),
            from_addr=ec.get("from", ""),
            recipients=ec.get("recipients", []),
            enabled=ec.get("enabled", True),
        ),
        NotifySlack(
            enabled=sc.get("enabled", False),
            webhook_url_files=sc.get("webhook_url_files", []),
        ),
    )


def validate_notify_channels(notify: dict) -> None:
    """Raise FimConfigError if the notify dict has no usable channel configured."""
    ec = notify.get("email", {})
    email_on = ec.get("enabled", True)
    if email_on and not ec.get("smtp_host"):
        raise FimConfigError("notify.yaml: email.smtp_host is required when email is enabled")
    slack_on = notify.get("slack", {}).get("enabled", False)
    if not email_on and not slack_on:
        raise FimConfigError("notify.yaml: at least one notification channel must be enabled")
