import hashlib
import logging
import socket
from pathlib import Path
from typing import Optional

from fim.config import Config
from fim.db import Db
from fim.git import git_status, git_diff, file_mtime
from fim.heartbeat import write_heartbeat
from fim.notify import build_channels, dispatch_notifications
from fim.report import _Report, print_verbose_report

log = logging.getLogger(__name__)


def _check_target(path: str, changed: dict, cfg: Config, db: Db,
                  report: Optional[_Report]) -> Optional[dict]:
    """Return detection dict for one target, or None if clean or suppressed."""
    status = changed.get(path, "")
    has_change = bool(status) and any(c in status for c in ("M", "D"))
    if report is not None:
        verdict = f"git={status or '':<3} → {'ALERT' if has_change else 'clean'}"
        report.target_lines.append(f"  {path:<58} {verdict}")
    if not has_change:
        return None
    log.warning("DETECTED: %s (status=%s)", path, status)
    diff = "(file deleted)" if "D" in status else git_diff(cfg.root_path, path)
    # hash the diff, not the file — same change twice suppresses,
    # different change re-alerts
    sha256 = hashlib.sha256(diff.encode()).hexdigest()
    suppressed = db.is_suppressed(path, sha256, cfg.suppress_window_hours)
    if report is not None:
        window = f"{cfg.suppress_window_hours}h"
        verdict = "suppressed" if suppressed else "NOT suppressed"
        report.suppression_lines.append(
            f"  {path}  sha256={sha256[:8]}...  window={window}  → {verdict}"
        )
    if suppressed:
        log.info("Suppressed: %s", path)
        return None
    return {
        "path": path,
        "full_path": str(Path(cfg.root_path) / path),
        "root_path": cfg.root_path,
        "git_status": status,
        "diff": diff,
        "mtime": file_mtime(cfg.root_path, path),
        "sha256": sha256,
    }


def run_detection(cfg: Config, db: Db,
                  report: Optional[_Report] = None) -> list:
    """Run git status and return list of unsuppressed detections.

    report is populated as a side-effect when verbose mode is active —
    capturing sha256 and suppression decisions in a single git pass.
    """
    changed = git_status(cfg.root_path)
    log.debug("git status: %d changed entries", len(changed))
    results = []
    for path in cfg.target_files:
        hit = _check_target(path, changed, cfg, db, report)
        if hit is not None:
            results.append(hit)
    return results


def _notify_and_record(channels: list, hostname: str, to_notify: list,
                       dry_run: bool, db: Db, report: Optional[_Report]) -> bool:
    sent = dispatch_notifications(channels, hostname, to_notify, dry_run)
    if report is not None:
        if dry_run:
            report.notification_lines.append("  (dry-run: no notifications sent)")
        else:
            for ch in channels:
                report.notification_lines.append(
                    f"  {ch.__class__.__name__} → {'sent' if sent else 'FAILED'}"
                )
    if not sent:
        log.error("One or more notification channels failed")
        return False
    if not dry_run:
        for d in to_notify:
            db.record(d["path"], d["sha256"])
    return True


def _populate_config_report(cfg: Config, channels: list, report: _Report) -> None:
    channel_names = ", ".join(
        c.__class__.__name__.replace("Channel", "").lower() for c in channels
    )
    report.config_lines = [
        f"  root_path       : {cfg.root_path}",
        f"  hostname        : {socket.gethostname()}",
        f"  state_db        : {cfg.state_db}",
        f"  suppress_window : {cfg.suppress_window_hours}h",
        f"  target_files    : {len(cfg.target_files)} files",
        f"  channels        : {channel_names}",
    ]


def run(cfg: Config, dry_run: bool = False, verbose: bool = False) -> int:
    """Run one detection cycle. Return 0 on success, 1 on any error."""
    log.info("eccube-fim check start (dry_run=%s)", dry_run)
    report = _Report() if verbose else None
    channels = build_channels(cfg)
    if report is not None:
        _populate_config_report(cfg, channels, report)
    try:
        db = Db(cfg.state_db)
    except Exception as e:
        log.error("DB error: %s", e)
        return 1
    exit_code = 0
    try:
        to_notify = run_detection(cfg, db, report)
        if to_notify:
            ok = _notify_and_record(channels, socket.gethostname(),
                                    to_notify, dry_run, db, report)
            exit_code = 0 if ok else 1
        else:
            log.info("No new alerts")
    except Exception as e:
        log.error("Detection error: %s", e)
        exit_code = 1
    finally:
        db.close()            # Db owns the connection; must close even on exception
        write_heartbeat(cfg)  # must always update; external monitor alerts if stale
        if report is not None:
            report.heartbeat_line = (
                f"  Written: {cfg.heartbeat_file}"
                if cfg.heartbeat_enabled else "  (disabled)"
            )
    if report is not None:
        print_verbose_report(report)
    log.info("eccube-fim check done")
    return exit_code
