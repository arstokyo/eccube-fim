import string
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from fim.detection import Detection
from fim.utils import JST

# Public constants — importable by template_ops.py without coupling to internals.
BUILTIN_TEMPLATE_DIR: Path = Path(__file__).parent / "templates"
TEMPLATE_NAMES: dict[str, str] = {
    "subject": "message_subject.txt",
    "email":   "email_body.txt",
    "slack":   "slack_body.txt",
}


def _load(name: str, config_dir: Optional[str] = None) -> string.Template:
    if config_dir is not None:
        candidate = Path(config_dir) / "templates" / name
        if candidate.exists():
            return string.Template(candidate.read_text(encoding="utf-8"))
    return string.Template((BUILTIN_TEMPLATE_DIR / name).read_text(encoding="utf-8"))


def _render_body(template_name: str, hostname: str, detections: list[Detection],
                 block_fmt: Callable[[Detection], str],
                 config_dir: Optional[str] = None) -> str:
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    file_blocks = "\n\n".join(block_fmt(d) for d in detections)
    return _load(template_name, config_dir).substitute(
        detected_at=now_str,
        hostname=hostname,
        file_count=len(detections),
        file_blocks=file_blocks,
    )


def render_subject(hostname: str, config_dir: Optional[str] = None) -> str:
    """Render the alert email subject line."""
    return _load(TEMPLATE_NAMES["subject"], config_dir).substitute(hostname=hostname).strip()


def render_email_body(hostname: str, detections: list[Detection],
                      config_dir: Optional[str] = None) -> str:
    """Render operator-facing email body: per-file path + diff in plain text."""
    def _fmt(d: Detection) -> str:
        return f"--- {d.full_path} ---\n{d.diff}"
    return _render_body(TEMPLATE_NAMES["email"], hostname, detections, _fmt, config_dir)


def render_slack_body(hostname: str, detections: list[Detection],
                      config_dir: Optional[str] = None) -> str:
    """Render engineer-facing Slack body: per-file diff in Markdown code blocks."""
    def _fmt(d: Detection) -> str:
        return f"*ファイル:* {d.full_path}\n```\n{d.diff}\n```"
    return _render_body(TEMPLATE_NAMES["slack"], hostname, detections, _fmt, config_dir)
