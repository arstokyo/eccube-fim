import string
from datetime import datetime
from pathlib import Path
from typing import Callable

from fim.utils import JST

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_SUBJECT_TMPL = "message_subject.txt"
_EMAIL_BODY_TMPL = "email_body.txt"
_SLACK_BODY_TMPL = "slack_body.txt"


def _load(name: str) -> string.Template:
    return string.Template((_TEMPLATE_DIR / name).read_text(encoding="utf-8"))


def _render_body(template_name: str, hostname: str, detections: list[dict],
                 block_fmt: Callable[[dict], str]) -> str:
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    file_blocks = "\n\n".join(block_fmt(d) for d in detections)
    return _load(template_name).substitute(
        detected_at=now_str,
        hostname=hostname,
        file_count=len(detections),
        file_blocks=file_blocks,
    )


def render_subject(hostname: str) -> str:
    """Render the alert email subject line."""
    return _load(_SUBJECT_TMPL).substitute(hostname=hostname).strip()


def render_email_body(hostname: str, detections: list[dict]) -> str:
    """Render operator-facing email body: per-file path + diff in plain text."""
    def _fmt(d: dict) -> str:
        return f"--- {d.get('full_path', d['path'])} ---\n{d['diff']}"
    return _render_body(_EMAIL_BODY_TMPL, hostname, detections, _fmt)


def render_slack_body(hostname: str, detections: list[dict]) -> str:
    """Render engineer-facing Slack body: per-file diff in Markdown code blocks."""
    def _fmt(d: dict) -> str:
        path = d.get("full_path", d["path"])
        return f"*ファイル:* {path}\n```\n{d['diff']}\n```"
    return _render_body(_SLACK_BODY_TMPL, hostname, detections, _fmt)
