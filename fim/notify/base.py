from typing import Protocol


class Channel(Protocol):
    def send(self, hostname: str, detections: list) -> bool:
        """Send one batched notification for all detected files. Return True if sent."""
        ...
