import pytest
from fim.cli import _build_parser
from fim.cli_commands import (
    cmd_db_list, cmd_db_clear, cmd_log,
    cmd_validate,
    cmd_target_list, cmd_target_add, cmd_target_remove,
    cmd_template_list, cmd_template_show, cmd_template_edit,
    cmd_template_reset, cmd_template_preview,
)


def test_no_command_has_no_func():
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


def test_config_target_no_action_shows_help(capsys):
    args = _build_parser().parse_args(["config", "target"])
    rc = args.func(args, None)
    assert rc == 0
    assert "ACTION" in capsys.readouterr().out


def test_config_template_no_action_shows_help(capsys):
    args = _build_parser().parse_args(["config", "template"])
    rc = args.func(args, None)
    assert rc == 0
    assert "ACTION" in capsys.readouterr().out


def test_db_subcommand_routes_correctly():
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


def test_config_validate_routes_correctly():
    args = _build_parser().parse_args(["config", "validate"])
    assert args.func is cmd_validate
    assert args.needs_config is True
    assert args.needs_root is True


def test_config_target_list_routes_correctly():
    args = _build_parser().parse_args(["config", "target", "list"])
    assert args.func is cmd_target_list
    assert args.needs_root is True


def test_config_target_add_routes_correctly():
    args = _build_parser().parse_args(
        ["config", "target", "add", "app/template/default/Shopping/index.twig"]
    )
    assert args.func is cmd_target_add
    assert args.file_path == "app/template/default/Shopping/index.twig"


def test_config_target_remove_routes_correctly():
    args = _build_parser().parse_args(
        ["config", "target", "remove", "app/template/default/Shopping/index.twig"]
    )
    assert args.func is cmd_target_remove


def test_config_template_list_routes_correctly():
    args = _build_parser().parse_args(["config", "template", "list"])
    assert args.func is cmd_template_list
    assert args.needs_root is True


def test_config_template_show_routes_correctly():
    args = _build_parser().parse_args(["config", "template", "show", "email"])
    assert args.func is cmd_template_show
    assert args.name == "email"


def test_config_template_edit_routes_correctly():
    args = _build_parser().parse_args(["config", "template", "edit", "slack"])
    assert args.func is cmd_template_edit
    assert args.name == "slack"


def test_config_template_reset_routes_correctly():
    args = _build_parser().parse_args(["config", "template", "reset", "subject"])
    assert args.func is cmd_template_reset
    assert args.name == "subject"


def test_config_template_preview_routes_correctly():
    args = _build_parser().parse_args(["config", "template", "preview"])
    assert args.func is cmd_template_preview


# Verify that old top-level commands no longer exist
def test_validate_not_top_level():
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["validate"])
    assert exc_info.value.code != 0


def test_target_not_top_level():
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["target", "list"])
    assert exc_info.value.code != 0


def test_template_not_top_level():
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["template", "list"])
    assert exc_info.value.code != 0
