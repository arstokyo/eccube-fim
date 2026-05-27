from common.exceptions import FimConfigError  # noqa: F401


class FimGitError(Exception):
    """Raised when a git subprocess fails or returns unexpected output."""


class FimDbError(Exception):
    """Raised when the SQLite state DB cannot be opened or written."""
