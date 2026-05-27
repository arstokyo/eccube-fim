from common.migration import MigrationRunner, _discover  # noqa: F401

from pathlib import Path

import yaml

from fim.config import DEFAULT_STATE_DB


def run_migrations(config_dir: str) -> int:
    """Apply all pending FIM migrations. Convenience wrapper for the CLI."""
    db_path = _resolve_db_path(config_dir)
    migrations_dir = str(Path(__file__).parent / "migrations")
    return MigrationRunner(db_path, migrations_dir, config_dir).run()


def _resolve_db_path(config_dir: str) -> str:
    """Read state_db from daemon.yaml; fall back to DEFAULT_STATE_DB if unreadable."""
    daemon_yaml = Path(config_dir) / "daemon.yaml"
    try:
        with open(daemon_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return str(data.get("state_db", DEFAULT_STATE_DB))
    except OSError:
        return DEFAULT_STATE_DB
