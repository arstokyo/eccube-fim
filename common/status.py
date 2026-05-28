import json
import os
from pathlib import Path
from typing import Any


def atomic_write_json(data: dict[str, Any], status_file: str) -> bool:
    """Write data as JSON to status_file atomically with 644 permissions.

    Creates parent directory if needed. Returns True on success, False on OSError.
    Callers log the warning if False is returned.
    """
    try:
        Path(status_file).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(status_file).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        # 644: web process (apache/www-data) can read; JSON contains no credentials
        os.chmod(tmp, 0o644)
        tmp.rename(status_file)
        return True
    except OSError:
        return False
