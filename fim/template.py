import string
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from fim.utils import JST

# Public constants — importable by template_ops.py without coupling to internals.
BUILTIN_TEMPLATE_DIR: Path = Path(__file__).parent / "templates"
TEMPLATE_NAMES: dict[str, str] = {
    "subject": "message_subject.txt",
    "email":   "email_body.txt",
    "slack":   "slack_body.txt",
}

# Module-level override dir — set once by main() via set_override_dir().
_override_dir: Optional[Path] = None


def set_override_dir(config_dir: str) -> None:
    """Point the template loader at the user override directory.

    Called once by cli.main() after parsing --config-dir. Not thread-safe;
    intended for single-process CLI use only.
    """
    global _override_dir
    _override_dir = Path(config_dir) / "templates"


def _load(name: str) -> string.Template:
    if _override_dir is not None:
        candidate = _override_dir / name
        if candidate.exists():
            return string.Template(candidate.read_text(encoding="utf-8"))
    return string.Template((BUILTIN_TEMPLATE_DIR / name).read_text(encoding="utf-8"))


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
    return _load(TEMPLATE_NAMES["subject"]).substitute(hostname=hostname).strip()


def render_email_body(hostname: str, detections: list[dict]) -> str:
    """Render operator-facing email body: per-file path + diff in plain text."""
    def _fmt(d: dict) -> str:
        return f"--- {d.get('full_path', d['path'])} ---\n{d['diff']}"
    return _render_body(TEMPLATE_NAMES["email"], hostname, detections, _fmt)


def render_slack_body(hostname: str, detections: list[dict]) -> str:
    """Render engineer-facing Slack body: per-file diff in Markdown code blocks."""
    def _fmt(d: dict) -> str:
        path = d.get("full_path", d["path"])
        return f"*ファイル:* {path}\n```\n{d['diff']}\n```"
    return _render_body(TEMPLATE_NAMES["slack"], hostname, detections, _fmt)
