import string
from datetime import datetime
from pathlib import Path

from fim.utils import JST

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _load(name: str) -> string.Template:
    return string.Template((_TEMPLATE_DIR / name).read_text(encoding="utf-8"))


def render_subject(hostname: str) -> str:
    """Render email subject. Supports $hostname for operator customisation."""
    return _load("message_subject.txt").substitute(hostname=hostname).strip()


def render_body(hostname: str, detection: dict) -> str:
    """Render shared body for one detected file (email and Slack)."""
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    return _load("message_body.txt").substitute(
        detected_at=now_str,
        hostname=hostname,
        full_path=detection.get("full_path", detection["path"]),
        root_path=detection.get("root_path", ""),
        diff=detection["diff"],
    )
