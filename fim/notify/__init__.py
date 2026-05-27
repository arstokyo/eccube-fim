import logging
from datetime import datetime
from typing import Optional, Type

from common.notify import build_channels, send_safe  # noqa: F401
from common.notify.base import Channel, RenderedNotification
from common.notify.email import EmailChannel
from common.notify.slack import SlackChannel
from fim.config import Config
from fim.detection import Detection
from fim.template import render_subject, render_email_body, render_slack_body
from fim.utils import JST

log = logging.getLogger(__name__)

_CHANNEL_CLASSES: dict[str, Type[Channel]] = {
    "email": EmailChannel,
    "slack": SlackChannel,
}


def _render(hostname: str, detections: list[Detection],
            config_dir: Optional[str] = None) -> RenderedNotification:
    # render once per channel format — adding a new format means one new key here
    return RenderedNotification(
        subject=render_subject(hostname, config_dir),
        bodies={
            "email": render_email_body(hostname, detections, config_dir),
            "slack": render_slack_body(hostname, detections, config_dir),
        },
    )


def dispatch_notifications(channels: list[Channel], hostname: str,
                            detections: list[Detection], dry_run: bool,
                            config_dir: Optional[str] = None) -> bool:
    """Render templates once, then send to every channel. Return True if all succeeded."""
    if dry_run:
        log.info("dry-run: skipping %d detection(s)", len(detections))
        return True
    notification = _render(hostname, detections, config_dir)
    results = [send_safe(ch, notification) for ch in channels]
    return all(results)


def send_test_notification(
    cfg: Config, hostname: str, channel_name: Optional[str] = None
) -> dict[str, bool]:
    """Send a test notification on the named channel, or all enabled if not given.

    Return dict mapping channel class name → send result.
    """
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    test_detection = Detection(
        path="(test)", full_path="(test)", root_path=cfg.root_path,
        git_status="", diff="(This is a test — no tampering was detected.)",
        mtime=now, sha256="",
    )
    channels = build_channels(cfg)
    if channel_name is not None:
        target = _CHANNEL_CLASSES[channel_name]
        channels = [ch for ch in channels if isinstance(ch, target)]
    notification = _render(hostname, [test_detection], cfg.config_dir)
    return {
        ch.__class__.__name__: send_safe(ch, notification)
        for ch in channels
    }
