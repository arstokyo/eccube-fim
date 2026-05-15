class FimConfigError(Exception):
    """Raised when a config file (daemon.yaml, targets.yaml, or notify.yaml) is missing, unreadable, or invalid."""


class FimGitError(Exception):
    """Raised when a git subprocess fails or returns unexpected output."""


class FimDbError(Exception):
    """Raised when the SQLite state DB cannot be opened or written."""
