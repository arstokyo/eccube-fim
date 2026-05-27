from dataclasses import dataclass, field
from pathlib import Path

from common.config import load_yaml as _load_yaml
from common.constants import (  # noqa: F401  — backward compat re-export
    DEFAULT_CONFIG_DIR,
    DEFAULT_SMTP_PORT,
    INSTALL_SBIN_DIR,
    INSTALL_LIB_DIR,
    INSTALL_SYSTEMD_DIR,
    VERSION_CHECK_STAMP,
    INSTALL_STATUS_DIR,
    INSTALL_STATUS_FILE,
)
from common.notify_config import NotifyEmail, NotifySlack  # noqa: F401
from common.exceptions import FimConfigError

# FIM-specific constants (not shared with malware)
DEFAULT_STATE_DB        = "/etc/eccube-fim/state.db"
DEFAULT_HEARTBEAT_FILE  = "/run/eccube-fim/heartbeat"
DEFAULT_SUPPRESS_HOURS  = 1
INSTALL_TIMER_NAME      = "eccube-fim-check.timer"
INSTALL_SERVICE_NAME    = "eccube-fim-check.service"
INSTALL_LOGROTATE_PATH  = "/etc/logrotate.d/eccube-fim"
INSTALL_TMPFILES_PATH   = "/etc/tmpfiles.d/eccube-fim.conf"


@dataclass
class Config:
    """Complete runtime configuration for eccube-fim."""
    root_path: str
    target_files: list[str]
    email: NotifyEmail
    slack: NotifySlack
    suppress_window_hours: int = DEFAULT_SUPPRESS_HOURS
    state_db: str = DEFAULT_STATE_DB
    heartbeat_enabled: bool = True
    heartbeat_file: str = DEFAULT_HEARTBEAT_FILE
    config_dir: str = DEFAULT_CONFIG_DIR


def validate_targets(data: dict) -> None:
    """Raise FimConfigError if the targets dict is structurally invalid."""
    if not data.get("target_files"):
        raise FimConfigError("targets.yaml: 'target_files' is required and must not be empty")


def load_config(config_dir: str = DEFAULT_CONFIG_DIR) -> Config:
    """Load daemon.yaml + targets.yaml + notify.yaml from config_dir."""
    d = Path(config_dir)
    main    = _load_yaml(d / "daemon.yaml")
    targets = _load_yaml(d / "targets.yaml")
    notify  = _load_yaml(d / "notify.yaml")
    _validate(main, targets, notify)
    cfg = _parse(main, targets, notify)
    cfg.config_dir = config_dir
    return cfg


def _validate(main: dict, targets: dict, notify: dict) -> None:
    if "root_path" not in main:
        raise FimConfigError("daemon.yaml: missing required key 'root_path'")
    if not targets.get("target_files"):
        raise FimConfigError("targets.yaml: 'target_files' is required and must not be empty")
    ec = notify.get("email", {})
    email_on = ec.get("enabled", True)
    if email_on and not ec.get("smtp_host"):
        raise FimConfigError("notify.yaml: email.smtp_host is required when email is enabled")
    slack_on = notify.get("slack", {}).get("enabled", False)
    if not email_on and not slack_on:
        raise FimConfigError("notify.yaml: at least one notification channel must be enabled")


def _parse(main: dict, targets: dict, notify: dict) -> Config:
    ec = notify.get("email", {})
    sc = notify.get("slack", {})
    hb = main.get("heartbeat", {})
    return Config(
        root_path=main["root_path"],
        target_files=targets.get("target_files", []),
        email=NotifyEmail(
            smtp_host=ec.get("smtp_host", ""),
            smtp_port=ec.get("smtp_port", DEFAULT_SMTP_PORT),
            smtp_user=ec.get("smtp_user", ""),
            smtp_password_file=ec.get("smtp_password_file", ""),
            from_addr=ec.get("from", ""),
            recipients=ec.get("recipients", []),
            enabled=ec.get("enabled", True),
        ),
        slack=NotifySlack(
            enabled=sc.get("enabled", False),
            webhook_url_files=sc.get("webhook_url_files", []),
        ),
        suppress_window_hours=targets.get("deduplication", {}).get(
            "suppress_window_hours", DEFAULT_SUPPRESS_HOURS),
        state_db=main.get("state_db", DEFAULT_STATE_DB),
        heartbeat_enabled=hb.get("enabled", True),
        heartbeat_file=hb.get("file", DEFAULT_HEARTBEAT_FILE),
    )
