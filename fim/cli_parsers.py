import argparse

from fim.cli_commands import (
    cmd_config_show, cmd_config_edit,
    cmd_target_list, cmd_target_add, cmd_target_remove,
    cmd_template_list, cmd_template_show, cmd_template_edit,
    cmd_template_reset, cmd_template_preview,
    cmd_status, cmd_db_list, cmd_db_clear, cmd_log,
)


def add_status_parser(sub: argparse._SubParsersAction) -> None:
    sub.add_parser(
        "status",
        help="print operational dashboard (service, heartbeat, DB, last log)",
    ).set_defaults(func=cmd_status, needs_config=True, needs_root=True)


def add_db_parser(sub: argparse._SubParsersAction) -> None:
    dp = sub.add_parser("db", help="inspect or clear the deduplication state database")
    dsub = dp.add_subparsers(dest="db_cmd", metavar="ACTION")
    dsub.required = True

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


def add_config_parser(sub: argparse._SubParsersAction) -> None:
    cp = sub.add_parser("config", help="view or edit configuration files")
    csub = cp.add_subparsers(dest="config_cmd", metavar="ACTION")
    csub.required = True

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


def add_target_parser(sub: argparse._SubParsersAction) -> None:
    tp = sub.add_parser("target", help="manage monitored file list in targets.yaml")
    tsub = tp.add_subparsers(dest="target_cmd", metavar="ACTION")
    tsub.required = True

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


def add_template_parser(sub: argparse._SubParsersAction) -> None:
    tp = sub.add_parser("template", help="list, view, edit, or reset notification templates")
    tsub = tp.add_subparsers(dest="template_cmd", metavar="ACTION")
    tsub.required = True

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
