from pathlib import Path

import yaml

from common.exceptions import FimConfigError


def load_yaml(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except OSError as e:
        raise FimConfigError(f"Cannot read {path.name}: {e}") from e
