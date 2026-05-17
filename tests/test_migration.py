import sqlite3
import textwrap
from pathlib import Path

import pytest

from fim.migration import (
    MigrationRunner,
    _discover,
    _resolve_db_path,
    run_migrations,
)


def _runner(tmp_path: Path) -> MigrationRunner:
    r = MigrationRunner.__new__(MigrationRunner)
    r._config_dir = str(tmp_path)
    r._db_path = str(tmp_path / "state.db")
    r._migrations_dir = tmp_path / "migrations"
    r._migrations_dir.mkdir()
    return r


def _write_migration(d: Path, num: int, body: str = "def run(config_dir): pass\n") -> None:
    (d / f"{num:04d}_test.py").write_text(body)


def test_run_returns_zero_when_no_migrations(tmp_path):
    assert _runner(tmp_path).run() == 0


def test_run_applies_migration_and_records_it(tmp_path):
    r = _runner(tmp_path)
    _write_migration(r._migrations_dir, 1)
    assert r.run() == 1
    conn = sqlite3.connect(r._db_path)
    rows = conn.execute("SELECT id, name FROM schema_migrations").fetchall()
    conn.close()
    assert rows == [(1, "0001_test.py")]


def test_run_skips_already_applied(tmp_path):
    r = _runner(tmp_path)
    _write_migration(r._migrations_dir, 1)
    assert r.run() == 1
    assert r.run() == 0


def test_run_raises_on_migration_failure(tmp_path):
    r = _runner(tmp_path)
    _write_migration(r._migrations_dir, 1, "def run(config_dir): raise ValueError('boom')\n")
    with pytest.raises(RuntimeError, match="boom"):
        r.run()


def test_run_does_not_record_failed_migration(tmp_path):
    r = _runner(tmp_path)
    _write_migration(r._migrations_dir, 1, "def run(config_dir): raise ValueError('boom')\n")
    try:
        r.run()
    except RuntimeError:
        pass
    conn = sqlite3.connect(r._db_path)
    has_table = bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone())
    rows = conn.execute("SELECT id FROM schema_migrations").fetchall() if has_table else []
    conn.close()
    assert rows == []


def test_run_applies_migrations_in_numeric_order(tmp_path):
    r = _runner(tmp_path)
    for n in [3, 1, 2]:
        (r._migrations_dir / f"{n:04d}_test.py").write_text(
            f"def run(config_dir): open(config_dir + '/{n}', 'w').close()\n"
        )
    r.run()
    order = sorted(int(p.name) for p in Path(r._config_dir).iterdir() if p.name.isdigit())
    assert order == [1, 2, 3]


def test_discover_finds_and_sorts_ignores_init(tmp_path):
    (tmp_path / "0002_b.py").write_text("")
    (tmp_path / "0001_a.py").write_text("")
    (tmp_path / "__init__.py").write_text("")
    assert [mid for mid, _ in _discover(tmp_path)] == [1, 2]


def test_resolve_db_path_reads_daemon_yaml(tmp_path):
    (tmp_path / "daemon.yaml").write_text("state_db: /custom/state.db\nroot_path: /x\n")
    assert _resolve_db_path(str(tmp_path)) == "/custom/state.db"


def test_resolve_db_path_falls_back_on_missing_yaml(tmp_path):
    from fim.config import DEFAULT_STATE_DB
    assert _resolve_db_path(str(tmp_path)) == DEFAULT_STATE_DB


def test_run_migrations_delegates_to_runner(tmp_path, monkeypatch):
    r = _runner(tmp_path)
    _write_migration(r._migrations_dir, 1)
    monkeypatch.setattr("fim.migration.MigrationRunner", lambda config_dir: r)
    assert run_migrations(str(tmp_path)) == 1


def test_is_applied_skips_run(tmp_path):
    """is_applied=True → run() never called, migration recorded."""
    mig_src = textwrap.dedent("""\
        import sqlite3

        def is_applied(conn):
            return True

        def run(config_dir):
            raise AssertionError("run() must not be called when is_applied() is True")
    """)
    r = _runner(tmp_path)
    (r._migrations_dir / "0001_test.py").write_text(mig_src, encoding="utf-8")
    count = r.run()
    assert count == 1
    conn = sqlite3.connect(r._db_path)
    rows = conn.execute("SELECT id FROM schema_migrations").fetchall()
    conn.close()
    assert rows == [(1,)]


def test_is_applied_false_calls_run(tmp_path):
    """is_applied=False → run() called, migration recorded."""
    mig_src = textwrap.dedent("""\
        import sqlite3

        def is_applied(conn):
            return False

        def run(config_dir):
            pass  # idempotent no-op
    """)
    r = _runner(tmp_path)
    (r._migrations_dir / "0001_test.py").write_text(mig_src, encoding="utf-8")
    count = r.run()
    assert count == 1
