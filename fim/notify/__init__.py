import logging

from fim.config import Config
from fim.notify.base import Channel
from fim.notify.email import EmailChannel
from fim.notify.slack import SlackChannel

log = logging.getLogger(__name__)


def build_channels(cfg: Config) -> list[Channel]:
    """Construct enabled channels with their config slices."""
    channels = []
    if cfg.email.enabled:
        channels.append(EmailChannel(cfg.email))
    if cfg.slack.enabled:
        channels.append(SlackChannel(cfg.slack))
    return channels


def dispatch_notifications(channels: list[Channel], hostname: str,
                            detections: list[dict], dry_run: bool) -> bool:
    """Send one batched notification per channel. Return True if every send succeeded."""
    if dry_run:
        log.info("dry-run: skipping %d detection(s)", len(detections))
        return True
    results = [_send_safe(ch, hostname, detections) for ch in channels]
    return all(results)


def _send_safe(channel: Channel, hostname: str, detections: list[dict]) -> bool:
    try:
        return channel.send(hostname, detections)
    except Exception as e:
        log.error("%s failed: %s", channel.__class__.__name__, e)
        return False
