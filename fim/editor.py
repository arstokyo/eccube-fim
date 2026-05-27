import os
import sys

from common.editor import file_hash as _file_hash, open_in_editor  # noqa: F401
from fim.config import Config, NotifyEmail, NotifySlack, load_config
from fim.validate import validate_config
from fim.exceptions import FimConfigError

_VALID_FILES = {"daemon", "targets", "notify"}


def edit_config_file(config_dir: str, which: str) -> int:
    """Open one of daemon/targets/notify YAML in $EDITOR; validate after save.

    Return 0 on success, 1 on validation error or when editor could not be opened.
    """
    if which not in _VALID_FILES:
        print(
            f"Unknown config file: {which!r}. Choose one of: {', '.join(sorted(_VALID_FILES))}",
            file=sys.stderr,
        )
        return 1
    path = os.path.join(config_dir, f"{which}.yaml")
    if not os.path.exists(path):
        print(f"Not found: {path}", file=sys.stderr)
        return 1
    before = _file_hash(path)
    if not open_in_editor(path):
        return 1
    if _file_hash(path) == before:
        print("No changes made.")
        return 0
    try:
        cfg = load_config(config_dir)
    except FimConfigError as e:
        print(f"Config error after edit — fix before next check:\n  {e}", file=sys.stderr)
        return 1
    # show full validation report so operator sees git tracking + secret file status
    validate_config(cfg)
    return 0


def show_config(cfg: Config, config_dir: str) -> None:
    """Print a human-readable summary of all three config files."""
    print(f"Config dir : {config_dir}")
    print()
    print("[daemon.yaml]")
    print(f"  root_path       : {cfg.root_path}")
    print(f"  state_db        : {cfg.state_db}")
    hb_status = "enabled" if cfg.heartbeat_enabled else "disabled"
    print(f"  heartbeat       : {hb_status}  ({cfg.heartbeat_file})")
    print()
    print("[targets.yaml]")
    print(f"  suppress_window : {cfg.suppress_window_hours}h")
    print(f"  target_files ({len(cfg.target_files)}):")
    for f in cfg.target_files:
        print(f"    {f}")
    print()
    print("[notify.yaml]")
    _show_email(cfg.email)
    _show_slack(cfg.slack)


def _show_email(email: NotifyEmail) -> None:
    status = "enabled" if email.enabled else "disabled"
    print(f"  email  : {status}")
    if not email.enabled:
        return
    print(f"    smtp : {email.smtp_host}:{email.smtp_port} (as {email.smtp_user})")
    print(f"    from : {email.from_addr}")
    recip = ", ".join(email.recipients) if email.recipients else "(none)"
    print(f"    to   : {recip}")


def _show_slack(slack: NotifySlack) -> None:
    status = "enabled" if slack.enabled else "disabled"
    print(f"  slack  : {status}")
    if not slack.enabled:
        return
    for f in slack.webhook_url_files:
        print(f"    webhook : {f}")
