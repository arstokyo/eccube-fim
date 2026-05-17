import logging
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

from fim.config import NotifyEmail
from fim.template import render_subject, render_email_body

log = logging.getLogger(__name__)

_SMTP_CONNECT_TIMEOUT = 10


class EmailChannel:
    """Sends alert emails via SMTP with STARTTLS."""

    def __init__(self, cfg: NotifyEmail) -> None:
        self._cfg = cfg

    def send(self, hostname: str, detections: list) -> bool:
        try:
            subject = render_subject(hostname)
            body = render_email_body(hostname, detections)
            _send_smtp(self._cfg, subject, body)
            return True
        except Exception as e:
            log.error("Email send failed: %s", e)
            return False


def _send_smtp(cfg: NotifyEmail, subject: str, body: str) -> None:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = cfg.from_addr
    msg["To"] = ", ".join(cfg.recipients)
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port,
                      timeout=_SMTP_CONNECT_TIMEOUT) as s:
        s.starttls()
        if cfg.smtp_user:
            password = Path(cfg.smtp_password_file).read_text(encoding="utf-8").strip()
            s.login(cfg.smtp_user, password)
        s.sendmail(cfg.from_addr, cfg.recipients, msg.as_string())
        # known: smtplib does not expose EHLO response; cannot assert STARTTLS offered
