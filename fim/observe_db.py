import sqlite3
import sys
from datetime import datetime
from typing import Optional

from fim.config import Config
from fim.utils import JST


def db_list(cfg: Config) -> int:
    """Print all notification deduplication records. Return 0."""
    conn = None
    try:
        conn = sqlite3.connect(cfg.state_db)
        rows = conn.execute(
            "SELECT file_path, content_sha256, last_notified_at "
            "FROM notifications ORDER BY last_notified_at DESC"
        ).fetchall()
    except (sqlite3.Error, OSError) as e:
        print(f"Cannot read state DB: {e}", file=sys.stderr)
        return 1
    finally:
        if conn:
            conn.close()
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
    """Remove all dedup records, or only those for `file_path`. Return 0."""
    target = f"'{file_path}'" if file_path else "ALL records"
    if not yes:
        answer = input(f"Clear {target} from state DB? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return 0
    conn = None
    try:
        conn = sqlite3.connect(cfg.state_db)
        with conn:
            cur = conn.cursor()
            try:
                if file_path:
                    cur.execute("DELETE FROM notifications WHERE file_path=?", (file_path,))
                else:
                    cur.execute("DELETE FROM notifications")
                n = cur.rowcount
            finally:
                cur.close()
    except (sqlite3.Error, OSError) as e:
        print(f"Cannot clear state DB: {e}", file=sys.stderr)
        return 1
    finally:
        if conn:
            conn.close()
    noun = "record" if n == 1 else "records"
    print(f"Removed {n} {noun} from state DB.")
    return 0
