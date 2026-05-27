import importlib.util
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from common.utils import JST

_DDL = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        id         INTEGER PRIMARY KEY,
        name       TEXT    NOT NULL,
        applied_at INTEGER NOT NULL
    )
"""


class MigrationRunner:
    """Discovers and applies pending versioned migrations."""

    def __init__(self, db_path: str, migrations_dir: str, config_dir: str) -> None:
        self._db_path        = db_path
        self._migrations_dir = Path(migrations_dir)
        self._config_dir     = config_dir

    def run(self) -> int:
        """Apply all pending migrations in numeric order. Return count applied."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(_DDL)
            conn.commit()
            done = {r[0] for r in conn.execute("SELECT id FROM schema_migrations").fetchall()}
            pending = [(mid, p) for mid, p in _discover(self._migrations_dir) if mid not in done]
            for mid, path in pending:
                _apply_one(conn, mid, path, self._config_dir)
        finally:
            conn.close()
        return len(pending)


def _discover(migrations_dir: Path) -> list[tuple[int, Path]]:
    entries = []
    for p in migrations_dir.glob("*.py"):
        if p.name == "__init__.py":
            continue
        prefix = p.stem.split("_", 1)[0]
        if not prefix.isdigit():
            continue
        entries.append((int(prefix), p))
    return sorted(entries)


def _load_migration(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load migration module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _apply_one(conn: sqlite3.Connection, mid: int, path: Path, config_dir: str) -> None:
    mod = _load_migration(path)
    if hasattr(mod, "is_applied") and mod.is_applied(conn):
        _record(conn, mid, path.name)
        return
    try:
        mod.run(config_dir)
    except Exception as e:
        raise RuntimeError(f"Migration {path.name} failed: {e}") from e
    _record(conn, mid, path.name)


def _record(conn: sqlite3.Connection, mid: int, name: str) -> None:
    conn.execute(
        "INSERT INTO schema_migrations (id, name, applied_at) VALUES (?,?,?)",
        (mid, name, int(datetime.now(JST).timestamp())),
    )
    conn.commit()
