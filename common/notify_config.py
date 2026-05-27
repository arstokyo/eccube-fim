from dataclasses import dataclass, field

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
