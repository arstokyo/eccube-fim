import sqlite3
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional

from fim.exceptions import FimDbError
from fim.utils import JST

_DDL = """
    CREATE TABLE IF NOT EXISTS notifications (
        file_path        TEXT    NOT NULL,
        content_sha256   TEXT    NOT NULL,
        last_notified_at INTEGER NOT NULL,
        PRIMARY KEY (file_path, content_sha256)
    )
"""


def db_transaction(f: Callable) -> Callable:
    @wraps(f)
    def wrapper(self: "Db", *args: Any, **kwargs: Any) -> Any:
        with self._conn:   # auto-commits or rolls back on exception
            cur = self._conn.cursor()
            try:
                return f(self, cur, *args, **kwargs)
            finally:
                cur.close()
    return wrapper


class Db:
    """SQLite state store for notification deduplication."""

    def __init__(self, db_path: str) -> None:
        try:
            self._conn = sqlite3.connect(db_path)
            self._conn.execute(_DDL)
            self._conn.commit()
        except sqlite3.OperationalError as e:
            raise FimDbError(f"Cannot open state DB '{db_path}': {e}") from e

    def __enter__(self) -> "Db":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    def is_suppressed(self, file_path: str, sha256: str, hours: int) -> bool:
        """Return True if an identical alert was already sent within `hours`."""
        # read-only SELECT; @db_transaction not needed — no mutation or rollback required
        row = self._conn.execute(
            "SELECT last_notified_at FROM notifications "
            "WHERE file_path=? AND content_sha256=?",
            (file_path, sha256),
        ).fetchone()
        if not row:
            return False
        # store as Unix int — datetime.fromisoformat() cannot parse timezone-aware
        # strings on Python 3.9 (fixed in 3.11)
        return (datetime.now(JST).timestamp() - row[0]) / 3600 < hours

    @db_transaction
    def record(self, cur: sqlite3.Cursor, file_path: str, sha256: str) -> None:
        cur.execute(
            "INSERT OR REPLACE INTO notifications "
            "(file_path, content_sha256, last_notified_at) VALUES (?,?,?)",
            (file_path, sha256, int(datetime.now(JST).timestamp())),
        )

    @db_transaction
    def list_records(self, cur: sqlite3.Cursor) -> list:
        """Return all (file_path, content_sha256, last_notified_at) rows, newest first."""
        return cur.execute(
            "SELECT file_path, content_sha256, last_notified_at "
            "FROM notifications ORDER BY last_notified_at DESC"
        ).fetchall()

    @db_transaction
    def clear_records(self, cur: sqlite3.Cursor,
                      file_path: Optional[str] = None) -> int:
        """Delete records for file_path (or all records if None). Return count deleted."""
        if file_path:
            cur.execute("DELETE FROM notifications WHERE file_path=?", (file_path,))
        else:
            cur.execute("DELETE FROM notifications")
        return cur.rowcount

    def record_count(self) -> int:
        """Return total number of suppressed-file records. Returns 0 on DB error."""
        # read-only SELECT; @db_transaction not needed — no mutation or rollback required
        try:
            row = self._conn.execute("SELECT COUNT(*) FROM notifications").fetchone()
            return row[0] if row else 0
        except sqlite3.Error:
            return 0
