from dataclasses import dataclass
from typing import Protocol


@dataclass
class RenderedNotification:
    """Pre-rendered content ready to be sent by any channel."""
    subject: str              # email subject line; channels that don't use it ignore it
    bodies: dict[str, str]    # keyed by channel name: "email", "slack"


class Channel(Protocol):
    def send(self, notification: RenderedNotification) -> bool:
        """Send the pre-rendered notification. Return True if sent."""
        ...
