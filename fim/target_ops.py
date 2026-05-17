import re
import sys
from pathlib import Path

import yaml

from fim.config import load_config
from fim.diagnostics import is_git_tracked
from fim.exceptions import FimConfigError


def _targets_path(config_dir: str) -> Path:
    return Path(config_dir) / "targets.yaml"


def list_targets(config_dir: str) -> int:
    """Print all monitored file paths. Return 0."""
    path = _targets_path(config_dir)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as e:
        print(f"Cannot read targets.yaml: {e}", file=sys.stderr)
        return 1
    files: list[str] = data.get("target_files") or []
    if not files:
        print("No files monitored. Add with: eccube-fim target add <path>")
        return 0
    for f in files:
        print(f"  {f}")
    print(f"\n{len(files)} file(s) monitored")
    return 0


def add_target(config_dir: str, file_path: str) -> int:
    """Append file_path to targets.yaml, preserving existing comments.

    Return 0 on success, 1 on error.
    """
    path = _targets_path(config_dir)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Cannot read targets.yaml: {e}", file=sys.stderr)
        return 1
    data = yaml.safe_load(text) or {}
    if file_path in (data.get("target_files") or []):
        print(f"Already monitored: {file_path}")
        return 0
    path.write_text(_insert_target(text, file_path), encoding="utf-8")
    try:
        cfg = load_config(config_dir)
    except FimConfigError as e:
        print(f"Config error after change — please fix:\n  {e}", file=sys.stderr)
        return 1
    print(f"Added: {file_path}")
    _warn_if_not_git_tracked(cfg.root_path, file_path)
    return 0


def _insert_target(text: str, file_path: str) -> str:
    """Return text with file_path appended inside the target_files block."""
    lines = text.splitlines(keepends=True)
    insert_after = _last_target_entry_index(lines)
    new_line = f"  - {file_path}\n"
    lines.insert(insert_after + 1, new_line)
    return "".join(lines)


def remove_target(config_dir: str, file_path: str) -> int:
    """Remove file_path from targets.yaml.

    Return 0 on success (including when path was not present), 1 on error.
    """
    path = _targets_path(config_dir)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Cannot read targets.yaml: {e}", file=sys.stderr)
        return 1
    data = yaml.safe_load(text) or {}
    if file_path not in (data.get("target_files") or []):
        print(f"Not monitored (nothing to remove): {file_path}")
        return 0
    lines = text.splitlines(keepends=True)
    target_line = re.compile(r"^\s+-\s+" + re.escape(file_path) + r"\s*$")
    # rstrip: splitlines(keepends=True) keeps \n; regex $ is ambiguous with trailing newline
    lines = [line for line in lines if not target_line.match(line.rstrip("\n"))]
    path.write_text("".join(lines), encoding="utf-8")
    return _validate_and_report(config_dir, f"Removed: {file_path}")


def _warn_if_not_git_tracked(root_path: str, file_path: str) -> None:
    if not is_git_tracked(root_path, file_path):
        print(
            f"Warning: '{file_path}' may not be tracked in git — "
            "run 'eccube-fim validate' to confirm.",
            file=sys.stderr,
        )


def _last_target_entry_index(lines: list[str]) -> int:
    """Return index after which to insert a new entry in the target_files block.

    Returns the index of the last existing '  - ...' entry, or the index of the
    'target_files:' key itself when the block is empty — so insert(result+1, ...)
    always lands inside the block, even if a sibling key follows it.
    Stops scanning when a new top-level YAML key is encountered after target_files.
    """
    key_idx = -1
    last = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("target_files:"):
            key_idx = i
            continue
        if key_idx != -1:
            if re.match(r"^\s+-\s+\S", line):
                last = i
            elif stripped and not stripped.startswith("#") and not line.startswith(" "):
                break
    return last if last != -1 else key_idx


def _validate_and_report(config_dir: str, success_msg: str) -> int:
    try:
        load_config(config_dir)
        print(success_msg)
        return 0
    except FimConfigError as e:
        print(f"Config error after change — please fix:\n  {e}", file=sys.stderr)
        return 1
