import logging
from pathlib import Path

from fim.config import Config

log = logging.getLogger(__name__)


def write_heartbeat(cfg: Config) -> None:
    if not cfg.heartbeat_enabled:
        return
    try:
        p = Path(cfg.heartbeat_file)
        # /run is tmpfs on all systemd distros; dir disappears after reboot
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
    except OSError as e:
        log.error("Heartbeat write failed: %s", e)
