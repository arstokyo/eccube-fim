import argparse
import sys
from typing import Optional

from fim.config import Config, load_config, DEFAULT_CONFIG_DIR
from fim.exceptions import FimConfigError
from fim.log import setup_logging
from fim.version import warn_if_update, VERSION_CHECK_STAMP


def _cmd_check(args: argparse.Namespace, cfg: Config) -> int:
    from fim.check import run
    # rate-limited to once per 24h — check is on a 5-min systemd loop
    warn_if_update(VERSION_CHECK_STAMP)
    return run(cfg, dry_run=args.dry_run, verbose=args.verbose)


def _cmd_validate(args: argparse.Namespace, cfg: Config) -> int:
    from fim.diagnostics import validate_config
    warn_if_update()
    return 0 if validate_config(cfg) else 1


def _cmd_test_mail(args: argparse.Namespace, cfg: Config) -> int:
    from fim.diagnostics import send_test_mail
    warn_if_update()
    return send_test_mail(cfg)


def _cmd_approve(args: argparse.Namespace, cfg: Config) -> int:
    from fim.ops import approve_change
    warn_if_update()
    return 0 if approve_change(cfg, args.file_path, message=args.message) else 1


def _cmd_upgrade(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.upgrade import upgrade
    return upgrade(yes=args.yes)


def _cmd_uninstall(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.lifecycle import uninstall
    return uninstall(keep_config=args.keep_config, yes=args.yes)


def _add_check_parser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("check", help="run integrity check (used by systemd)")
    sp.add_argument("--dry-run", action="store_true",
                    help="detect without writing DB or sending notifications")
    sp.set_defaults(func=_cmd_check, needs_config=True)


def _add_validate_parser(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("validate",
                   help="validate configuration files and print status report"
                   ).set_defaults(func=_cmd_validate, needs_config=True)


def _add_test_mail_parser(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("test-mail",
                   help="send a test email to verify SMTP reachability"
                   ).set_defaults(func=_cmd_test_mail, needs_config=True)


def _add_approve_parser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("approve", help="approve a detected file change")
    sp.add_argument("file_path",
                    help="path relative to root_path "
                         "(e.g. app/template/default/Shopping/index.twig)")
    sp.add_argument("--message", "-m", default="", metavar="TEXT",
                    help="reason for approval (recorded in log)")
    sp.set_defaults(func=_cmd_approve, needs_config=True)


def _add_upgrade_parser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("upgrade", help="download and install the latest release")
    sp.add_argument("--yes", "-y", action="store_true",
                    help="skip confirmation prompt")
    sp.set_defaults(func=_cmd_upgrade, needs_config=False)


def _add_uninstall_parser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("uninstall", help="stop service and remove all installed files")
    sp.add_argument("--keep-config", action="store_true",
                    help="preserve /etc/eccube-fim (config, secrets, state.db)")
    sp.add_argument("--yes", "-y", action="store_true",
                    help="skip confirmation prompt")
    sp.set_defaults(func=_cmd_uninstall, needs_config=False)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="eccube-fim",
                                description="EC-CUBE file integrity monitoring")
    p.add_argument("--config-dir", default=DEFAULT_CONFIG_DIR, metavar="DIR",
                   help=f"Config directory (default: {DEFAULT_CONFIG_DIR})")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Structured diagnostic output on stdout + DEBUG log level")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    _add_check_parser(sub)
    _add_validate_parser(sub)
    _add_test_mail_parser(sub)
    _add_approve_parser(sub)
    _add_upgrade_parser(sub)
    _add_uninstall_parser(sub)
    return p


def main() -> int:
    args = _build_parser().parse_args()
    setup_logging(verbose=args.verbose)
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
