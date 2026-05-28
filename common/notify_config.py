from dataclasses import dataclass, field
from pathlib import Path

from common.constants import DEFAULT_SMTP_PORT


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


def print_secrets_status(email: "NotifyEmail", slack: "NotifySlack") -> None:
    """Print whether the SMTP password file and Slack webhook files exist on disk."""
    if email.enabled:
        pw_ok = bool(email.smtp_password_file) and Path(email.smtp_password_file).exists()
        print(f"Email recipients : {email.recipients or '(none)'}")
        print(f"SMTP password    : {'found' if pw_ok else 'NOT FOUND'} ({email.smtp_password_file})")
    if slack.enabled:
        for wh_file in slack.webhook_url_files:
            wh_ok = Path(wh_file).exists()
            print(f"Slack webhook    : {'found' if wh_ok else 'NOT FOUND'} ({wh_file})")
