import re
import sys
from pathlib import Path


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
