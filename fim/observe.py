# known: ~220 lines — observe subsystem; no natural split boundary
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Optional

from fim.config import Config, INSTALL_TIMER_NAME
from fim.db import Db
from fim.utils import JST, LOG_DIR

_LOG_PATH = LOG_DIR / "check.log"
_STALE_FALLBACK_SECS = 1800  # 2 × default 15-min interval; used when timer cannot be read
_WINDOW_SECS = 86400         # look-back window for "last error"


def _stale_threshold() -> int:
    """Return 2 × timer interval in seconds. Falls back to _STALE_FALLBACK_SECS."""
    try:
        r = subprocess.run(
            ["systemctl", "show", INSTALL_TIMER_NAME,
             "--property=OnCalendarSpec", "--value"],
            capture_output=True, text=True, check=False,
        )
        m = re.search(r"0/(\d+)", r.stdout.strip())
        if m:
            return int(m.group(1)) * 60 * 2
    except OSError:
        pass
    return _STALE_FALLBACK_SECS


# ── Format helpers ────────────────────────────────────────────────────────────

def parse_usec(raw: str) -> Optional[datetime]:
    try:
        usec = int(raw)
        return datetime.fromtimestamp(usec / 1_000_000, tz=JST) if usec else None
    except (ValueError, OverflowError, OSError):
        return None


def fmt_rel(secs: int) -> str:
    if secs < 0:
        return "overdue"
    if secs < 60:
        return f"in {secs}s"
    m = secs // 60
    return f"in {m}m {secs % 60}s" if secs % 60 else f"in {m}m"


def fmt_age(secs: int) -> str:
    if secs < 60:
        return f"{secs}s ago"
    m = secs // 60
    return f"{m}m ago" if m < 60 else f"{m // 60}h ago"


def log_ts(line: str) -> Optional[float]:
    """Parse 'YYYY-MM-DD HH:MM:SS' prefix → Unix timestamp, or None."""
    if len(line) < 19:
        return None
    try:
        return datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST).timestamp()
    except ValueError:
        return None


# ── Status dashboard ──────────────────────────────────────────────────────────

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
        next_dt = parse_usec(r2.stdout.strip()) or _query_timer_from_list()
        return state, next_dt
    except OSError:
        return "(systemd not available)", None


def _query_timer_from_list() -> Optional[datetime]:
    # NextElapseUSecRealtime returns 0 briefly after the timer fires on OL9;
    # list-timers for a specific unit is always populated.
    try:
        r = subprocess.run(
            ["systemctl", "list-timers", INSTALL_TIMER_NAME,
             "--no-legend", "--no-pager"],
            capture_output=True, text=True,
        )
        line = r.stdout.strip()
        if not line:
            return None
        parts = line.split()
        # output: DayOfWeek YYYY-MM-DD HH:MM:SS TZ LEFT ...
        return datetime.strptime(f"{parts[1]} {parts[2]}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)
    except (OSError, ValueError, IndexError):
        return None


def _print_heartbeat(cfg: Config, now: datetime) -> None:
    if not cfg.heartbeat_enabled:
        print("Heartbeat  : (disabled)")
        return
    try:
        mtime = os.path.getmtime(cfg.heartbeat_file)
        hb_dt = datetime.fromtimestamp(mtime, tz=JST)
        age = int(now.timestamp() - mtime)
        health = "OK" if age < _stale_threshold() else "STALE"
        print(f"Heartbeat  : {hb_dt.strftime('%Y-%m-%d %H:%M:%S JST')}  ({fmt_age(age)})  {health}")
    except OSError:
        print("Heartbeat  : (not found — service may not have run yet)")


def _print_db(cfg: Config) -> None:
    try:
        with Db(cfg.state_db) as db:
            n = db.record_count()
        print(f"\nDB records : {n} suppressed {'file' if n == 1 else 'files'}")
    except Exception:
        # intentionally not displayed — status board always shows something
        print("\nDB records : (unavailable)")


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


# ── DB operations ─────────────────────────────────────────────────────────────

def db_list(cfg: Config) -> int:
    """Print all notification deduplication records. Return 0."""
    try:
        with Db(cfg.state_db) as db:
            rows = db.list_records()
    except Exception as e:
        print(f"Cannot read state DB: {e}", file=sys.stderr)
        return 1
    if not rows:
        print("No suppressed files in state DB.")
        return 0
    print(f"  {'FILE':<54} {'SHA256':<14}  LAST NOTIFIED")
    print("  " + "-" * 84)
    for path, sha, ts in rows:
        dt = datetime.fromtimestamp(ts, tz=JST).strftime("%Y-%m-%d %H:%M:%S JST")
        print(f"  {path:<54} {sha[:12]:<14}  {dt}")
    print(f"\n{len(rows)} record(s)")
    return 0


def db_clear(cfg: Config, file_path: Optional[str], yes: bool) -> int:
    """Remove all dedup records, or only those for file_path. Return 0."""
    target = f"'{file_path}'" if file_path else "ALL records"
    if not yes:
        answer = input(f"Clear {target} from state DB? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return 0
    try:
        with Db(cfg.state_db) as db:
            n = db.clear_records(file_path)
    except Exception as e:
        print(f"Cannot clear state DB: {e}", file=sys.stderr)
        return 1
    noun = "record" if n == 1 else "records"
    print(f"Removed {n} {noun} from state DB.")
    return 0


# ── Log operations ────────────────────────────────────────────────────────────

def log_tail(lines: int, level: Optional[str]) -> int:
    """Print the last `lines` entries from check.log, optionally filtered by level.

    Return 0 on success, 1 if the log file is absent or unreadable.
    """
    try:
        with open(_LOG_PATH, encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except FileNotFoundError:
        print(f"Log file not found: {_LOG_PATH}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Cannot read log: {e}", file=sys.stderr)
        return 1
    if level:
        tag = f" {level.upper()} "
        all_lines = [ln for ln in all_lines if tag in ln]
    tail = all_lines[-lines:]
    for ln in tail:
        print(ln, end="")
    if not tail:
        label = f"{level.upper()} " if level else ""
        print(f"(no {label}log entries)")
    return 0
