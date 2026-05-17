import pytest

from fim.cli import _build_parser
from fim.version import __version__


def test_version_flag_short(capsys):
    with pytest.raises(SystemExit) as exc:
        _build_parser().parse_args(["-v"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_version_flag_long(capsys):
    with pytest.raises(SystemExit) as exc:
        _build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_version_output_includes_prog_name(capsys):
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["--version"])
    assert "eccube-fim" in capsys.readouterr().out


def test_verbose_still_works_without_short_flag():
    args = _build_parser().parse_args(["--verbose", "check"])
    assert args.verbose is True
