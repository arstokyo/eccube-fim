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


def _cmd_test(args: argparse.Namespace, cfg: Config) -> int:
    from fim.ops import validate_config, send_test_mail
    warn_if_update()
    if args.validate:
        return 0 if validate_config(cfg) else 1
    if args.send_test_mail:
        return send_test_mail(cfg)
    return 0  # unreachable — mutually exclusive group is required


def _cmd_update(args: argparse.Namespace, cfg: Config) -> int:
    from fim.ops import approve_change
    warn_if_update()
    return 0 if approve_change(cfg, args.file_path, message=args.message) else 1


def _add_check_parser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("check", help="run integrity check (used by systemd)")
    sp.add_argument("--dry-run", action="store_true",
                    help="detect without writing DB or sending notifications")
    sp.set_defaults(func=_cmd_check, needs_config=True)


def _add_test_parser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("test", help="validate config and test notifications")
    tg = sp.add_mutually_exclusive_group(required=True)
    tg.add_argument("--validate", action="store_true",
                    help="validate configuration files and print status report")
    tg.add_argument("--send-test-mail", action="store_true",
                    help="send a test email to verify SMTP reachability")
    sp.set_defaults(func=_cmd_test, needs_config=True)


def _add_update_parser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("update", help="approve a detected file change")
    sp.add_argument("file_path",
                    help="path relative to root_path "
                         "(e.g. app/template/default/Shopping/index.twig)")
    sp.add_argument("--message", "-m", default="", metavar="TEXT",
                    help="reason for approval (recorded in log)")
    sp.set_defaults(func=_cmd_update, needs_config=True)


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
    _add_test_parser(sub)
    _add_update_parser(sub)
    # future: _add_config_parser(sub)  needs_config=False
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
