import logging
import socket
from datetime import datetime
from typing import Callable, Optional, Type

from fim.config import Config
from fim.detection import Detection
from fim.notify.base import Channel, RenderedNotification
from fim.notify.email import EmailChannel
from fim.notify.slack import SlackChannel
from fim.template import render_subject, render_email_body, render_slack_body
from fim.utils import JST

log = logging.getLogger(__name__)

# Each entry: (enabled_predicate, factory).
# To add a new channel: append one tuple here.
_CHANNEL_BUILDERS: list[tuple[Callable[[Config], bool], Callable[[Config], Channel]]] = [
    (lambda cfg: cfg.email.enabled, lambda cfg: EmailChannel(cfg.email)),
    (lambda cfg: cfg.slack.enabled, lambda cfg: SlackChannel(cfg.slack)),
]

# name→class map used by send_test_notification to filter to a single channel.
# Keys must match the channel_name strings accepted by the CLI.
_CHANNEL_CLASSES: dict[str, Type[Channel]] = {
    "email": EmailChannel,
    "slack": SlackChannel,
}


def build_channels(cfg: Config) -> list[Channel]:
    """Construct all enabled channels from the registry."""
    return [factory(cfg) for check, factory in _CHANNEL_BUILDERS if check(cfg)]


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
    results = [_send_safe(ch, notification) for ch in channels]
    return all(results)


def _send_safe(channel: Channel, notification: RenderedNotification) -> bool:
    try:
        return channel.send(notification)
    except Exception as e:
        log.error("%s failed: %s", channel.__class__.__name__, e)
        return False


def send_test_notification(
    cfg: Config, hostname: str, channel_name: Optional[str] = None
) -> dict[str, bool]:
    """Send a test notification on the named channel, or all enabled if not given.

    Return dict mapping channel class name → send result,
    e.g. {"EmailChannel": True}.
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
        ch.__class__.__name__: _send_safe(ch, notification)
        for ch in channels
    }
