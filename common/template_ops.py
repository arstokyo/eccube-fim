import re
import shutil
import string
import sys
from pathlib import Path
from typing import Any, Optional

from common.editor import file_hash, open_in_editor


def user_template_dir(config_dir: str) -> Path:
    return Path(config_dir) / "templates"


def resolve_template(config_dir: str, name: str,
                     template_names: dict[str, str], builtin_dir: Path) -> tuple[Path, bool]:
    """Return (path, is_override). is_override=True when a user override exists."""
    fname = template_names[name]
    override = user_template_dir(config_dir) / fname
    if override.exists():
        return override, True
    return builtin_dir / fname, False


def unknown_template(name: str, template_names: dict[str, str]) -> None:
    valid = ", ".join(sorted(template_names))
    print(f"Unknown template: {name!r}. Choose one of: {valid}", file=sys.stderr)


def validate_template_vars(path: Path, name: str,
                           required_vars: dict[str, set[str]], cycle: str = "check") -> None:
    """Warn if the saved template omits a variable required by the renderer.

    Uses regex extraction rather than string.Template.substitute() — substitute()
    raises only on unknown variables, not on missing ones; regex detects absences.
    """
    text = path.read_text(encoding="utf-8")
    used = set(re.findall(r"\$\{?([a-zA-Z_]\w*)\}?", text))
    missing = required_vars.get(name, set()) - used
    if missing:
        missing_str = ", ".join(f"${v}" for v in sorted(missing))
        print(
            f"Warning: template '{name}' is missing required variable(s): "
            f"{missing_str} — the next {cycle} cycle may fail to render.",
            file=sys.stderr,
        )


def list_templates_impl(config_dir: str,
                        template_names: dict[str, str], builtin_dir: Path) -> int:
    """Print all template names and whether a user override is active."""
    fw = max(len(fname) for fname in template_names.values()) + 2
    print(f"{'NAME':<10} {'FILE':<{fw}} {'SOURCE'}")
    print("-" * (fw + 18))
    for name, fname in sorted(template_names.items()):
        _, is_override = resolve_template(config_dir, name, template_names, builtin_dir)
        source = f"override ({user_template_dir(config_dir)})" if is_override else "built-in"
        print(f"  {name:<8} {fname:<{fw}} {source}")
    return 0


def show_template_impl(config_dir: str, name: str,
                       template_names: dict[str, str], builtin_dir: Path) -> int:
    """Print the active template content (override preferred)."""
    if name not in template_names:
        unknown_template(name, template_names)
        return 1
    path, is_override = resolve_template(config_dir, name, template_names, builtin_dir)
    source = "override" if is_override else "built-in"
    print(f"# {path}  [{source}]")
    print(path.read_text(encoding="utf-8"))
    return 0


def edit_template_impl(config_dir: str, name: str,
                       template_names: dict[str, str], builtin_dir: Path,
                       required_vars: dict[str, Any], cycle: str) -> int:
    """Open (or create) the override template in $EDITOR.

    Creates the override dir and copies the built-in on first use.
    """
    if name not in template_names:
        unknown_template(name, template_names)
        return 1
    udir = user_template_dir(config_dir)
    udir.mkdir(exist_ok=True)
    override_path = udir / template_names[name]
    if not override_path.exists():
        shutil.copy2(builtin_dir / template_names[name], override_path)
        print(f"Copied built-in to {override_path}")
    before = file_hash(str(override_path))
    if not open_in_editor(str(override_path)):
        return 1
    if file_hash(str(override_path)) == before:
        print("No changes made.")
        return 0
    validate_template_vars(override_path, name, required_vars, cycle=cycle)
    print(f"Template saved: {override_path}")
    return 0


def reset_template_impl(config_dir: str, name: str,
                        template_names: dict[str, str], builtin_dir: Path) -> int:
    """Delete the user override so the built-in resumes."""
    if name not in template_names:
        unknown_template(name, template_names)
        return 1
    override_path = user_template_dir(config_dir) / template_names[name]
    if not override_path.exists():
        print(f"No override for '{name}' — already using built-in")
        return 0
    override_path.unlink()
    print(f"Override removed. Built-in template restored for '{name}'.")
    return 0


def load_template(name: str, builtin_dir: Path,
                  config_dir: Optional[str] = None) -> string.Template:
    """Return a Template from a user override if present, else from builtin_dir."""
    if config_dir is not None:
        candidate = Path(config_dir) / "templates" / name
        if candidate.exists():
            return string.Template(candidate.read_text(encoding="utf-8"))
    return string.Template((builtin_dir / name).read_text(encoding="utf-8"))
