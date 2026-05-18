import argparse
from typing import Optional

from fim.config import Config
from fim.cli_commands import (
    cmd_config_show, cmd_config_edit, cmd_config_timer, cmd_config_setup_notify,
    cmd_validate,
    cmd_target_list, cmd_target_add, cmd_target_remove,
    cmd_template_list, cmd_template_show, cmd_template_edit,
    cmd_template_reset, cmd_template_preview,
)


def add_config_parser(sub: argparse._SubParsersAction) -> None:  # known: 48 lines — declarative parser registration, no logic boundary
    cp = sub.add_parser("config", help="view or edit configuration files")
    csub = cp.add_subparsers(dest="config_cmd", metavar="ACTION")

    def _help(args: argparse.Namespace, cfg: Optional[Config]) -> int:
        cp.print_help()
        return 0

    cp.set_defaults(func=_help, needs_config=False, needs_root=False)

    csub.add_parser(
        "show",
        help="print effective configuration from all three YAML files",
    ).set_defaults(func=cmd_config_show, needs_config=True, needs_root=True)

    ep = csub.add_parser("edit", help="open a config file in $EDITOR and validate after save")
    ep.add_argument(
        "file",
        nargs="?",
        choices=["daemon", "targets", "notify"],
        default="targets",
        help="which file to edit (default: targets)",
    )
    ep.set_defaults(func=cmd_config_edit, needs_config=False, needs_root=True)

    timer_sp = csub.add_parser(
        "timer",
        help="show or change the check interval (e.g. 5, 30, 1h)",
    )
    timer_sp.add_argument(
        "interval",
        nargs="?",
        metavar="INTERVAL",
        help="new interval: number = minutes (1–60) or '1h' (e.g. 5, 30, 1h)",
    )
    timer_sp.set_defaults(func=cmd_config_timer, needs_config=False, needs_root=True)

    csub.add_parser(
        "setup-notify",
        help="interactive wizard to enable or reconfigure email/Slack notifications",
    ).set_defaults(func=cmd_config_setup_notify, needs_config=False, needs_root=True)

    csub.add_parser(
        "validate",
        help="validate configuration files and print status report",
    ).set_defaults(func=cmd_validate, needs_config=True, needs_root=True)

    _add_config_target_parser(csub)
    _add_config_template_parser(csub)


def _add_config_target_parser(csub: argparse._SubParsersAction) -> None:
    tp = csub.add_parser("target", help="manage monitored file list in targets.yaml")
    tsub = tp.add_subparsers(dest="target_cmd", metavar="ACTION")

    def _help(args: argparse.Namespace, cfg: Optional[Config]) -> int:
        tp.print_help()
        return 0

    tp.set_defaults(func=_help, needs_config=False, needs_root=False)

    tsub.add_parser(
        "list",
        help="print all monitored file paths",
    ).set_defaults(func=cmd_target_list, needs_config=False, needs_root=True)

    ap = tsub.add_parser("add", help="add a file to the monitored list")
    ap.add_argument("file_path",
                    help="path relative to root_path "
                         "(e.g. app/template/default/Shopping/index.twig)")
    ap.set_defaults(func=cmd_target_add, needs_config=False, needs_root=True)

    rp = tsub.add_parser("remove", help="remove a file from the monitored list")
    rp.add_argument("file_path", help="path relative to root_path")
    rp.set_defaults(func=cmd_target_remove, needs_config=False, needs_root=True)


def _add_config_template_parser(csub: argparse._SubParsersAction) -> None:
    tp = csub.add_parser("template", help="list, view, edit, or reset notification templates")
    tsub = tp.add_subparsers(dest="template_cmd", metavar="ACTION")

    def _help(args: argparse.Namespace, cfg: Optional[Config]) -> int:
        tp.print_help()
        return 0

    tp.set_defaults(func=_help, needs_config=False, needs_root=False)

    tsub.add_parser(
        "list",
        help="list all templates and show whether a user override is active",
    ).set_defaults(func=cmd_template_list, needs_config=False, needs_root=True)

    for action, fn, hlp in [
        ("show",  cmd_template_show,  "print the active template content"),
        ("edit",  cmd_template_edit,  "open (or create) the override in $EDITOR"),
        ("reset", cmd_template_reset, "delete override and revert to built-in"),
    ]:
        sp = tsub.add_parser(action, help=hlp)
        sp.add_argument("name", choices=["subject", "email", "slack"],
                        help="template name")
        sp.set_defaults(func=fn, needs_config=False, needs_root=True)

    tsub.add_parser(
        "preview",
        help="render all templates with sample data",
    ).set_defaults(func=cmd_template_preview, needs_config=False, needs_root=True)
