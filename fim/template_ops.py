import shutil
import socket
from pathlib import Path

from common.template_ops import (
    user_template_dir as _user_template_dir,
    resolve_template as _resolve_raw,
    unknown_template as _unknown_raw,
    validate_template_vars as _validate_template_vars_raw,
)
from fim._template_data import _REQUIRED_VARS, _SAMPLE_DETECTIONS
from common.editor import file_hash as _file_hash, open_in_editor
from fim.template import (
    BUILTIN_TEMPLATE_DIR, TEMPLATE_NAMES,
    render_subject, render_email_body, render_slack_body,
)


# Place these wrappers AFTER the TEMPLATE_NAMES, BUILTIN_TEMPLATE_DIR, and
# _REQUIRED_VARS constants are defined — they reference those names at call time.
def _resolve(config_dir: str, name: str) -> tuple[Path, bool]:
    return _resolve_raw(config_dir, name, TEMPLATE_NAMES, BUILTIN_TEMPLATE_DIR)


def list_templates(config_dir: str) -> int:
    """Print all template names + whether a user override is active."""
    print(f"{'NAME':<10} {'FILE':<30} {'SOURCE'}")
    print("-" * 65)
    for name, fname in sorted(TEMPLATE_NAMES.items()):
        _, is_override = _resolve(config_dir, name)
        source = f"override ({_user_template_dir(config_dir)})" if is_override else "built-in"
        print(f"  {name:<8} {fname:<30} {source}")
    return 0


def show_template(config_dir: str, name: str) -> int:
    """Print the active template content (override preferred)."""
    if name not in TEMPLATE_NAMES:
        _unknown(name)
        return 1
    path, is_override = _resolve(config_dir, name)
    source = "override" if is_override else "built-in"
    print(f"# {path}  [{source}]")
    print(path.read_text(encoding="utf-8"))
    return 0


def edit_template(config_dir: str, name: str) -> int:
    """Open (or create) the override template in $EDITOR.

    Creates the override dir and copies the built-in on first use.
    """
    if name not in TEMPLATE_NAMES:
        _unknown(name)
        return 1
    udir = _user_template_dir(config_dir)
    udir.mkdir(exist_ok=True)
    override_path = udir / TEMPLATE_NAMES[name]
    if not override_path.exists():
        shutil.copy2(BUILTIN_TEMPLATE_DIR / TEMPLATE_NAMES[name], override_path)
        print(f"Copied built-in to {override_path}")
    before = _file_hash(str(override_path))
    if not open_in_editor(str(override_path)):
        return 1
    if _file_hash(str(override_path)) == before:
        print("No changes made.")
        return 0
    _validate_template_vars(override_path, name)
    print(f"Template saved: {override_path}")
    return 0


def reset_template(config_dir: str, name: str) -> int:
    """Delete the user override so the built-in resumes."""
    if name not in TEMPLATE_NAMES:
        _unknown(name)
        return 1
    override_path = _user_template_dir(config_dir) / TEMPLATE_NAMES[name]
    if not override_path.exists():
        print(f"No override for '{name}' — already using built-in")
        return 0
    override_path.unlink()
    print(f"Override removed. Built-in template restored for '{name}'.")
    return 0


def preview_template(config_dir: str) -> int:
    """Render all templates with sample data and print the result."""
    hostname = socket.gethostname()
    print("=" * 60)
    print("SUBJECT")
    print("=" * 60)
    print(render_subject(hostname, config_dir))
    print()
    print("=" * 60)
    print("EMAIL BODY")
    print("=" * 60)
    print(render_email_body(hostname, _SAMPLE_DETECTIONS, config_dir))
    print()
    print("=" * 60)
    print("SLACK BODY")
    print("=" * 60)
    print(render_slack_body(hostname, _SAMPLE_DETECTIONS, config_dir))
    return 0


def _unknown(name: str) -> None:
    _unknown_raw(name, TEMPLATE_NAMES)


def _validate_template_vars(path: Path, name: str) -> None:
    _validate_template_vars_raw(path, name, _REQUIRED_VARS, cycle="check")
