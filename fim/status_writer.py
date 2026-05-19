import json
import logging
import os
import re
import socket
import time
from pathlib import Path
from typing import Any

from fim.config import (
    Config,
    INSTALL_STATUS_DIR, INSTALL_STATUS_FILE,
    INSTALL_SYSTEMD_DIR, INSTALL_TIMER_NAME,
)
from fim.db import Db
from fim.utils import LOG_DIR
from fim.version import __version__

log = logging.getLogger(__name__)

_LOG_INFO_LINES = 30
_DEFAULT_INTERVAL_SECS = 15 * 60   # fallback when timer unit is unreadable


def write_status(cfg: Config) -> None:
    """Write monitoring summary JSON to INSTALL_STATUS_FILE for the EC-CUBE plugin."""
    interval = _timer_interval_secs()
    suppressed_count, recent_detections = _get_db_data(cfg)
    data = {
        "schema_version": 1,
        "generated_at": int(time.time()),
        "hostname": socket.gethostname(),
        "daemon_version": __version__,
        "timer_interval_secs": interval,
        "heartbeat": _heartbeat_info(cfg, interval),
        "suppressed_count": suppressed_count,
        "recent_detections": recent_detections,
        "recent_log": _recent_log_lines(),
    }
    _atomic_write(data)


def _timer_interval_secs() -> int:
    try:
        text = (Path(INSTALL_SYSTEMD_DIR) / INSTALL_TIMER_NAME).read_text(encoding="utf-8")
        m = re.search(r"OnCalendar=\*:0/(\d+)", text)
        if m:
            return int(m.group(1)) * 60
    except OSError:
        pass
    return _DEFAULT_INTERVAL_SECS


def _heartbeat_info(cfg: Config, interval_secs: int) -> dict[str, Any]:
    if not cfg.heartbeat_enabled:
        return {"enabled": False}
    stale_threshold = interval_secs * 2   # 2 missed fires → genuinely stale
    try:
        mtime = os.path.getmtime(cfg.heartbeat_file)
        age = int(time.time() - mtime)
        return {
            "enabled": True,
            "last_seen_at": int(mtime),
            "age_seconds": age,
            "health": "OK" if age < stale_threshold else "STALE",
        }
    except OSError:
        return {"enabled": True, "last_seen_at": None, "age_seconds": None, "health": "NOT_FOUND"}


def _get_db_data(cfg: Config) -> tuple[int, list[dict[str, Any]]]:
    """Return (suppressed_count, recent_detections) from state DB in one connection."""
    try:
        with Db(cfg.state_db) as db:
            count = db.record_count()
            rows = db.list_records()
        detections = [{"file_path": r[0], "detected_at": r[2]} for r in rows[:20]]
        return count, detections
    except Exception as e:
        log.warning("Cannot read state DB: %s", e)
        return -1, []


def _recent_log_lines() -> list[str]:
    try:
        with open(LOG_DIR / "check.log", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return [ln.rstrip() for ln in lines if " INFO " in ln][-_LOG_INFO_LINES:]
    except OSError:
        return []


def _atomic_write(data: dict[str, Any]) -> None:
    try:
        Path(INSTALL_STATUS_DIR).mkdir(parents=True, exist_ok=True)
        tmp = Path(INSTALL_STATUS_FILE).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        # 644: web process (apache/www-data) can read; JSON contains no credentials
        os.chmod(tmp, 0o644)
        tmp.rename(INSTALL_STATUS_FILE)
    except OSError as e:
        log.warning("Cannot write status file: %s", e)
