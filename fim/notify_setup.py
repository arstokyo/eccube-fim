import sys

# Re-exported from common so the wizard's prompt/secret-write/validation helpers
# stay importable as fim.notify_setup.* (callers and tests bind to these names).
from common.notify_setup import (  # noqa: F401
    setup_notify_interactive as _setup_notify_interactive,
    _require_tty,
    _prompt,
    _ask_yes_no,
    _secure_write,
    _validate_email,
    _validate_email_inputs,
    _collect_email,
    _collect_slack,
    _load_raw_notify,
    _print_notify_status,
)
from common.exceptions import FimConfigError
from fim.config import load_config
from fim.validate import validate_config


def _validate(config_dir: str) -> int:
    try:
        cfg = load_config(config_dir)
    except FimConfigError as e:
        print(f"Config error — fix before next check:\n  {e}", file=sys.stderr)
        return 1
    print()
    return 0 if validate_config(cfg) else 1


def setup_notify_interactive(config_dir: str) -> int:
    """Interactive wizard to configure notification channels, validated as a FIM config."""
    return _setup_notify_interactive(config_dir, _validate)
