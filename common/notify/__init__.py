import logging
from typing import Protocol

from common.notify_config import NotifyEmail, NotifySlack
from common.notify.base import Channel, RenderedNotification
from common.notify.email import EmailChannel
from common.notify.slack import SlackChannel

log = logging.getLogger(__name__)


class NotifyConfigLike(Protocol):
    """Structural contract for any config that carries email + slack settings."""
    email: NotifyEmail
    slack: NotifySlack


def build_channels(cfg: NotifyConfigLike) -> list[Channel]:
    """Build all enabled channels from config. Works with Config and MalwareConfig."""
    channels: list[Channel] = []
    if cfg.email.enabled:
        channels.append(EmailChannel(cfg.email))
    if cfg.slack.enabled:
        channels.append(SlackChannel(cfg.slack))
    return channels


def send_safe(channel: Channel, notification: RenderedNotification) -> bool:
    """Send to one channel; return False (never raise) on any failure."""
    try:
        return channel.send(notification)
    except Exception as e:
        log.error("%s failed: %s", channel.__class__.__name__, e)
        return False
