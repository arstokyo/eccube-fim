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


# Registry: (predicate, factory). To add a channel: append one tuple here.
_REGISTRY = [
    (lambda cfg: cfg.email.enabled, lambda cfg: EmailChannel(cfg.email)),
    (lambda cfg: cfg.slack.enabled, lambda cfg: SlackChannel(cfg.slack)),
]


def build_channels(cfg: NotifyConfigLike) -> list[Channel]:
    """Build all enabled channels from config. Works with Config and MalwareConfig."""
    return [factory(cfg) for enabled, factory in _REGISTRY if enabled(cfg)]


def send_safe(channel: Channel, notification: RenderedNotification) -> bool:
    """Send to one channel; return False (never raise) on any failure."""
    try:
        return channel.send(notification)
    except Exception as e:
        log.error("%s failed: %s", channel.__class__.__name__, e)
        return False
