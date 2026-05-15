from typing import Protocol


class Channel(Protocol):
    def send(self, hostname: str, detection: dict) -> bool:
        """Send notification for one detected file. Return True if sent."""
        ...
