import argparse
from typing import Optional

from fim.config import Config
from fim.cli_commands import cmd_test_mail, cmd_test_slack


def add_test_parser(sub: argparse._SubParsersAction) -> None:
    tp = sub.add_parser(
        "test", help="send a test notification to verify channel reachability"
    )
    tsub = tp.add_subparsers(dest="test_cmd", metavar="CHANNEL")

    def _help(args: argparse.Namespace, cfg: Optional[Config]) -> int:
        tp.print_help()
        return 0

    tp.set_defaults(func=_help, needs_config=False, needs_root=False)

    tsub.add_parser(
        "mail",
        help="send a test email via SMTP",
    ).set_defaults(func=cmd_test_mail, needs_config=True, needs_root=True)

    tsub.add_parser(
        "slack",
        help="send a test Slack message via webhook",
    ).set_defaults(func=cmd_test_slack, needs_config=True, needs_root=True)
