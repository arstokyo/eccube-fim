import hashlib
import os
import subprocess
import sys
from pathlib import Path

from common.notify_config import NotifyEmail, NotifySlack

_EDITOR_FALLBACK = "vi"


def file_hash(path: str) -> str:
    """Return sha256 hex digest of file contents; empty string if file is missing."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""


def open_in_editor(path: str) -> bool:
    """Open `path` in $EDITOR (or vi). Blocks until the editor exits.

    Return True if the editor ran, False if the executable was not found.
    """
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or _EDITOR_FALLBACK
    try:
        subprocess.run([editor, path])
        return True
    except FileNotFoundError:
        print(f"Editor not found: {editor!r} — set $EDITOR to a valid executable.",
              file=sys.stderr)
        return False


# known: show_email/show_slack are notification display helpers co-located here
# to avoid a 2-function module; move to common/notify_display.py if a third is needed
def show_email(email: NotifyEmail) -> None:
    status = "enabled" if email.enabled else "disabled"
    print(f"  email  : {status}")
    if not email.enabled:
        return
    print(f"    smtp : {email.smtp_host}:{email.smtp_port} (as {email.smtp_user})")
    print(f"    from : {email.from_addr}")
    recip = ", ".join(email.recipients) if email.recipients else "(none)"
    print(f"    to   : {recip}")


def show_slack(slack: NotifySlack) -> None:
    status = "enabled" if slack.enabled else "disabled"
    print(f"  slack  : {status}")
    if not slack.enabled:
        return
    for f in slack.webhook_url_files:
        print(f"    webhook : {f}")
