import importlib.util
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from fim.config import DEFAULT_STATE_DB
from fim.utils import JST

_DDL = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        id         INTEGER PRIMARY KEY,
        name       TEXT    NOT NULL,
        applied_at INTEGER NOT NULL
    )
"""


class MigrationRunner:
    """Discovers and applies pending versioned migrations against state.db."""

    def __init__(self, config_dir: str) -> None:
        self._config_dir = config_dir
        self._db_path = _resolve_db_path(config_dir)
        self._migrations_dir = Path(__file__).parent / "migrations"

    def run(self) -> int:
        """Apply all pending migrations in numeric order. Return count applied.

        Raises RuntimeError if any migration fails; already-applied migrations
        are preserved (each is committed individually before the next starts).
        """
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


def _resolve_db_path(config_dir: str) -> str:
    """Read state_db from daemon.yaml; fall back to DEFAULT_STATE_DB if unreadable."""
    daemon_yaml = Path(config_dir) / "daemon.yaml"
    try:
        with open(daemon_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return str(data.get("state_db", DEFAULT_STATE_DB))
    except OSError:
        return DEFAULT_STATE_DB


def _discover(migrations_dir: Path) -> list[tuple[int, Path]]:
    """Return (id, path) pairs for all NNNN_*.py files, sorted by numeric prefix."""
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
    """Import a migration file by path; raise RuntimeError if it cannot be loaded."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load migration module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _apply_one(conn: sqlite3.Connection, mid: int, path: Path, config_dir: str) -> None:
    mod = _load_migration(path)
    try:
        mod.run(config_dir)
    except Exception as e:
        raise RuntimeError(f"Migration {path.name} failed: {e}") from e
    conn.execute(
        "INSERT INTO schema_migrations (id, name, applied_at) VALUES (?,?,?)",
        (mid, path.name, int(datetime.now(JST).timestamp())),
    )
    conn.commit()


def run_migrations(config_dir: str) -> int:
    """Apply all pending migrations and return count applied."""
    return MigrationRunner(config_dir).run()
