from dataclasses import dataclass


@dataclass
class Detection:
    """A single confirmed file-integrity event pending notification."""
    path: str
    full_path: str
    root_path: str
    git_status: str
    diff: str
    mtime: str
    sha256: str
