import argparse
from typing import Optional

from fim.config import Config
from fim.cli_commands import cmd_status, cmd_db_list, cmd_db_clear, cmd_log


def add_status_parser(sub: argparse._SubParsersAction) -> None:
    sub.add_parser(
        "status",
        help="print operational dashboard (service, heartbeat, DB, last log)",
    ).set_defaults(func=cmd_status, needs_config=True, needs_root=True)


def add_db_parser(sub: argparse._SubParsersAction) -> None:
    dp = sub.add_parser("db", help="inspect or clear the deduplication state database")
    dsub = dp.add_subparsers(dest="db_cmd", metavar="ACTION")

    def _help(args: argparse.Namespace, cfg: Optional[Config]) -> int:
        dp.print_help()
        return 0

    dp.set_defaults(func=_help, needs_config=False, needs_root=False)

    dsub.add_parser(
        "list",
        help="show all suppressed-file records",
    ).set_defaults(func=cmd_db_list, needs_config=True, needs_root=True)

    cp = dsub.add_parser("clear", help="remove dedup records (all or one file)")
    cp.add_argument(
        "--file", metavar="PATH",
        help="remove only records for this file path (relative to root_path)",
    )
    cp.add_argument("--yes", "-y", action="store_true",
                    help="skip confirmation prompt")
    cp.set_defaults(func=cmd_db_clear, needs_config=True, needs_root=True)


def add_log_parser(sub: argparse._SubParsersAction) -> None:
    lp = sub.add_parser("log", help="tail the eccube-fim check log")
    lp.add_argument(
        "--lines", "-n", type=int, default=20, metavar="N",
        help="number of lines to show (default: 20)",
    )
    lp.add_argument(
        "--level", metavar="LEVEL",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="filter to this log level only",
    )
    lp.set_defaults(func=cmd_log, needs_config=False, needs_root=True)
