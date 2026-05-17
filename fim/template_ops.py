import re
import shutil
import socket
import sys
from pathlib import Path

from fim._template_data import _REQUIRED_VARS, _SAMPLE_DETECTIONS
from fim.editor import open_in_editor
from fim.template import (
    BUILTIN_TEMPLATE_DIR, TEMPLATE_NAMES,
    render_subject, render_email_body, render_slack_body,
)


def _user_template_dir(config_dir: str) -> Path:
    return Path(config_dir) / "templates"


def _resolve(config_dir: str, name: str) -> tuple[Path, bool]:
    """Return (path, is_override). is_override=True when a user override exists."""
    fname = TEMPLATE_NAMES[name]
    override = _user_template_dir(config_dir) / fname
    if override.exists():
        return override, True
    return BUILTIN_TEMPLATE_DIR / fname, False


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
    open_in_editor(str(override_path))
    _validate_template_vars(override_path, name)
    print(f"Template saved: {override_path}")
    return 0


def _validate_template_vars(path: Path, name: str) -> None:
    """Warn if the saved template omits a variable required by the renderer.

    Uses regex extraction rather than string.Template.substitute() — substitute()
    raises only on unknown variables, not on missing ones; regex detects absences.
    """
    text = path.read_text(encoding="utf-8")
    used = set(re.findall(r"\$\{?([a-zA-Z_]\w*)\}?", text))
    missing = _REQUIRED_VARS.get(name, set()) - used
    if missing:
        missing_str = ", ".join(f"${v}" for v in sorted(missing))
        print(
            f"Warning: template '{name}' is missing required variable(s): "
            f"{missing_str} — the next check cycle may fail to render.",
            file=sys.stderr,
        )


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
    """Render all templates with sample data and print the result.

    Relies on set_override_dir() having been called by main() beforehand.
    """
    hostname = socket.gethostname()
    print("=" * 60)
    print("SUBJECT")
    print("=" * 60)
    print(render_subject(hostname))
    print()
    print("=" * 60)
    print("EMAIL BODY")
    print("=" * 60)
    print(render_email_body(hostname, _SAMPLE_DETECTIONS))
    print()
    print("=" * 60)
    print("SLACK BODY")
    print("=" * 60)
    print(render_slack_body(hostname, _SAMPLE_DETECTIONS))
    return 0


def _unknown(name: str) -> None:
    valid = ", ".join(sorted(TEMPLATE_NAMES))
    print(f"Unknown template: {name!r}. Choose one of: {valid}", file=sys.stderr)
