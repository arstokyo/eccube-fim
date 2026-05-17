import argparse
import sys
from typing import Optional

from fim.config import Config, load_config, DEFAULT_CONFIG_DIR
from fim.version import read_installed_version
from fim.exceptions import FimConfigError
from fim.lifecycle import _require_root
from fim.log import setup_logging
from fim.cli_commands import (
    cmd_check, cmd_validate, cmd_approve,
    cmd_upgrade, cmd_uninstall, cmd_migrate,
)
from fim.cli_parsers import (
    add_status_parser, add_db_parser, add_log_parser,
    add_config_parser, add_target_parser, add_template_parser,
)
from fim.cli_parsers_test import add_test_parser


def _add_check_parser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("check", help="run integrity check (used by systemd)")
    sp.add_argument("--dry-run", action="store_true",
                    help="detect without writing DB or sending notifications")
    sp.set_defaults(func=cmd_check, needs_config=True, needs_root=True)


def _add_validate_parser(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("validate",
                   help="validate configuration files and print status report"
                   ).set_defaults(func=cmd_validate, needs_config=True, needs_root=True)


def _add_approve_parser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("approve", help="approve a detected file change")
    sp.add_argument("file_path",
                    help="path relative to root_path "
                         "(e.g. app/template/default/Shopping/index.twig)")
    sp.add_argument("--message", "-m", default="", metavar="TEXT",
                    help="reason for approval (recorded in log)")
    sp.set_defaults(func=cmd_approve, needs_config=True, needs_root=True)


def _add_upgrade_parser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("upgrade", help="download and install the latest release")
    sp.add_argument("--yes", "-y", action="store_true",
                    help="skip confirmation prompt")
    sp.add_argument("--force", "-f", action="store_true",
                    help="reinstall even if already at the latest version")
    sp.set_defaults(func=cmd_upgrade, needs_config=False, needs_root=True)


def _add_migrate_parser(sub: argparse._SubParsersAction) -> None:
    # internal command called by install.sh --update; hidden from user-facing help
    sub.add_parser("_migrate", help=argparse.SUPPRESS).set_defaults(
        func=cmd_migrate, needs_config=False, needs_root=True,
    )


def _add_uninstall_parser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("uninstall", help="stop service and remove all installed files")
    sp.add_argument("--keep-config", action="store_true",
                    help="preserve /etc/eccube-fim (config, secrets, state.db)")
    sp.add_argument("--yes", "-y", action="store_true",
                    help="skip confirmation prompt")
    sp.set_defaults(func=cmd_uninstall, needs_config=False, needs_root=True)


def _build_parser() -> argparse.ArgumentParser:
    installed = read_installed_version()
    p = argparse.ArgumentParser(prog="eccube-fim",
                                description="EC-CUBE file integrity monitoring")
    p.add_argument("--version", "-v", action="version",
                   version=f"%(prog)s {installed}")
    p.add_argument("--config-dir", default=DEFAULT_CONFIG_DIR, metavar="DIR",
                   help=f"Config directory (default: {DEFAULT_CONFIG_DIR})")
    p.add_argument("--verbose", action="store_true",
                   help="Structured diagnostic output on stdout + DEBUG log level")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")
    _add_check_parser(sub)
    _add_validate_parser(sub)
    _add_approve_parser(sub)
    _add_upgrade_parser(sub)
    _add_uninstall_parser(sub)
    _add_migrate_parser(sub)
    add_status_parser(sub)
    add_db_parser(sub)
    add_log_parser(sub)
    add_test_parser(sub)
    add_config_parser(sub)
    add_target_parser(sub)
    add_template_parser(sub)
    return p


def main() -> int:
    p = _build_parser()
    args = p.parse_args()
    if not hasattr(args, "func"):
        p.print_help()
        return 0
    if getattr(args, "needs_root", False) and not _require_root():
        return 1
    setup_logging(verbose=args.verbose)
    from fim.template import set_override_dir
    set_override_dir(args.config_dir)
    cfg: Optional[Config] = None
    if getattr(args, "needs_config", True):
        try:
            cfg = load_config(args.config_dir)
        except FimConfigError as e:
            sys.stderr.write(f"Config error: {e}\n")
            return 1
    return args.func(args, cfg)


if __name__ == "__main__":
    sys.exit(main())
