from fim.cli import _build_parser
from fim.cli_commands import cmd_db_list, cmd_db_clear, cmd_log


def test_no_command_has_no_func():
    """Top-level: main() can detect missing command via hasattr(args, 'func')."""
    args = _build_parser().parse_args([])
    assert not hasattr(args, "func")


def test_no_command_help_exit_zero(capsys):
    p = _build_parser()
    args = p.parse_args([])
    if not hasattr(args, "func"):
        p.print_help()
    out = capsys.readouterr().out
    assert "COMMAND" in out
    assert "eccube-fim" in out


def test_db_no_action_shows_help(capsys):
    args = _build_parser().parse_args(["db"])
    rc = args.func(args, None)
    assert rc == 0
    assert "ACTION" in capsys.readouterr().out


def test_config_no_action_shows_help(capsys):
    args = _build_parser().parse_args(["config"])
    rc = args.func(args, None)
    assert rc == 0
    assert "ACTION" in capsys.readouterr().out


def test_target_no_action_shows_help(capsys):
    args = _build_parser().parse_args(["target"])
    rc = args.func(args, None)
    assert rc == 0
    assert "ACTION" in capsys.readouterr().out


def test_template_no_action_shows_help(capsys):
    args = _build_parser().parse_args(["template"])
    rc = args.func(args, None)
    assert rc == 0
    assert "ACTION" in capsys.readouterr().out


def test_db_subcommand_still_routes_correctly():
    """Removing required=True must not break normal subcommand routing."""
    args = _build_parser().parse_args(["db", "list"])
    assert args.func is cmd_db_list
    assert args.needs_config is True
    assert args.needs_root is True


def test_db_clear_routes_correctly():
    args = _build_parser().parse_args(["db", "clear", "--yes"])
    assert args.func is cmd_db_clear
    assert args.yes is True


def test_log_routes_correctly():
    args = _build_parser().parse_args(["log", "--lines", "5", "--level", "ERROR"])
    assert args.func is cmd_log
    assert args.lines == 5
    assert args.level == "ERROR"
