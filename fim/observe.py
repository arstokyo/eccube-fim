import os
import sqlite3
import subprocess
from datetime import datetime
from typing import Optional

from fim.config import Config, INSTALL_TIMER_NAME
from fim.utils import JST, LOG_DIR
from fim._observe_fmt import parse_usec, fmt_rel, fmt_age, log_ts
# Re-export: keep fim.observe as the single import surface for the CLI.
from fim.observe_db import db_list, db_clear  # noqa: F401
from fim.observe_log import log_tail           # noqa: F401

_LOG_PATH = LOG_DIR / "check.log"
_STALE_SECS = 600     # heartbeat older than 10 min → STALE
_WINDOW_SECS = 86400  # look-back window for "last error"


def status(cfg: Config) -> int:
    """Print the operational status dashboard. Return 0."""
    now = datetime.now(JST)
    print(f"=== eccube-fim status ({now.strftime('%Y-%m-%d %H:%M JST')}) ===\n")
    _print_service(now)
    _print_heartbeat(cfg, now)
    _print_db(cfg)
    _print_log(now)
    return 0


def _print_service(now: datetime) -> None:
    state, next_dt = _query_timer()
    print(f"Service    : {INSTALL_TIMER_NAME}  {state}")
    if next_dt is None:
        print("Next run   : (unavailable)")
        return
    secs = int((next_dt - now).total_seconds())
    print(f"Next run   : {next_dt.strftime('%Y-%m-%d %H:%M:%S JST')}  ({fmt_rel(secs)})")


def _query_timer() -> tuple[str, Optional[datetime]]:
    """Return (active_state, next_run_jst). Falls back gracefully on OSError."""
    try:
        r = subprocess.run(["systemctl", "is-active", INSTALL_TIMER_NAME],
                           capture_output=True, text=True)
        state = r.stdout.strip() or "unknown"
        r2 = subprocess.run(
            ["systemctl", "show", INSTALL_TIMER_NAME,
             "--property=NextElapseUSecRealtime", "--value"],
            capture_output=True, text=True,
        )
        return state, parse_usec(r2.stdout.strip())
    except OSError:
        return "(systemd not available)", None


def _print_heartbeat(cfg: Config, now: datetime) -> None:
    if not cfg.heartbeat_enabled:
        print("Heartbeat  : (disabled)")
        return
    try:
        mtime = os.path.getmtime(cfg.heartbeat_file)
        hb_dt = datetime.fromtimestamp(mtime, tz=JST)
        age = int(now.timestamp() - mtime)
        health = "OK" if age < _STALE_SECS else "STALE"
        print(f"Heartbeat  : {hb_dt.strftime('%Y-%m-%d %H:%M:%S JST')}  ({fmt_age(age)})  {health}")
    except OSError:
        print("Heartbeat  : (not found — service may not have run yet)")


def _print_db(cfg: Config) -> None:
    conn = None
    try:
        conn = sqlite3.connect(cfg.state_db)
        row = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()
        n = row[0] if row else 0
        print(f"\nDB records : {n} suppressed {'file' if n == 1 else 'files'}")
    except sqlite3.Error:
        # intentionally not displayed — status board always shows something
        print("\nDB records : (unavailable)")
    finally:
        if conn:
            conn.close()


def _print_log(now: datetime) -> None:
    print(f"Last action: {_last_line(' INFO ')}")
    print(f"Last error : {_last_error(now)}")


def _last_line(level: str) -> str:
    """Return the most-recent log line containing `level`, or a fallback string."""
    last = None
    try:
        with open(_LOG_PATH, encoding="utf-8", errors="replace") as f:
            for line in f:
                if level in line:
                    last = line.rstrip()
    except FileNotFoundError:
        return "(log file not found)"
    except OSError:
        return "(cannot read log)"
    return last or "(no entries)"


def _last_error(now: datetime) -> str:
    """Return the most-recent ERROR line within 24 h, or '(none in last 24h)'."""
    cutoff = now.timestamp() - _WINDOW_SECS
    last = None
    try:
        with open(_LOG_PATH, encoding="utf-8", errors="replace") as f:
            for line in f:
                if " ERROR " not in line:
                    continue
                ts = log_ts(line)
                if ts is not None and ts >= cutoff:
                    last = line.rstrip()
    except FileNotFoundError:
        return "(log file not found)"
    except OSError:
        return "(cannot read log)"
    return last or "(none in last 24h)"
