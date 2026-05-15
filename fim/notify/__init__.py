import logging

from fim.config import Config
from fim.notify.base import Channel
from fim.notify.email import EmailChannel
from fim.notify.slack import SlackChannel

log = logging.getLogger(__name__)


def build_channels(cfg: Config) -> list:
    """Construct enabled channels with their config slices."""
    channels = [EmailChannel(cfg.email)]
    if cfg.slack.enabled:
        # only added when configured — excluded from dispatch entirely when off
        channels.append(SlackChannel(cfg.slack))
    return channels


def dispatch_notifications(channels: list, hostname: str,
                            detected: list, dry_run: bool) -> bool:
    """Send one notification per detected file to all channels.
    Return True if every send succeeded."""
    if dry_run:
        log.info("dry-run: skipping %d detection(s)", len(detected))
        return True
    results = [
        _send_safe(ch, hostname, d)
        for d in detected
        for ch in channels
    ]
    return all(results)


def _send_safe(channel: Channel, hostname: str, detection: dict) -> bool:
    try:
        return channel.send(hostname, detection)
    except Exception as e:
        log.error("%s failed: %s", channel.__class__.__name__, e)
        return False
