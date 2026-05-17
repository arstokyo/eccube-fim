"""
Migration 0001 — baseline

Idempotency contract:
  is_applied(conn) must return True if and only if this migration's
  database changes are already present, regardless of whether the
  migration was applied via the runner or manually.

  run(config_dir) must be safe to call even when is_applied() returns
  False — use IF NOT EXISTS / IF EXISTS guards for all DDL.

Author checklist before shipping a new migration:
  [ ] is_applied() verifies the actual DB state, not just schema_migrations
  [ ] run() uses CREATE TABLE IF NOT EXISTS / DROP TABLE IF EXISTS / etc.
  [ ] run() is tested both on a fresh DB and a DB where is_applied() is True
"""
import sqlite3


def is_applied(conn: sqlite3.Connection) -> bool:
    """Return True when schema_migrations already exists in the database."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    )
    return cur.fetchone() is not None


def run(config_dir: str) -> None:
    # schema_migrations is bootstrapped by MigrationRunner._DDL before any
    # migration runs, so this migration is always a no-op in practice.
    pass
