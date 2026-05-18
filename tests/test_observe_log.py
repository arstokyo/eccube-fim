import builtins
from pathlib import Path
from unittest.mock import patch

import pytest

from fim.observe import log_tail


@pytest.fixture
def log_file(tmp_path):
    f = tmp_path / "check.log"
    f.write_text(
        "2026-05-17 10:00:00 INFO check started\n"
        "2026-05-17 10:00:01 DEBUG git diff empty\n"
        "2026-05-17 10:00:02 INFO check completed, 0 changes detected\n"
        "2026-05-17 10:05:00 ERROR smtp connection refused\n"
        "2026-05-17 10:10:00 INFO check completed, 1 change detected\n",
        encoding="utf-8",
    )
    return f


def test_log_tail_default(log_file, capsys, monkeypatch):
    monkeypatch.setattr("fim.observe._LOG_PATH", log_file)
    rc = log_tail(lines=20, level=None)
    assert rc == 0
    out = capsys.readouterr().out
    assert "check started" in out
    assert "check completed" in out
    assert "smtp connection refused" in out


def test_log_tail_limits_lines(log_file, capsys, monkeypatch):
    monkeypatch.setattr("fim.observe._LOG_PATH", log_file)
    log_tail(lines=2, level=None)
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 2
    assert "10:10:00" in out   # last line present
    assert "10:00:00" not in out  # first line absent


def test_log_tail_filter_error(log_file, capsys, monkeypatch):
    monkeypatch.setattr("fim.observe._LOG_PATH", log_file)
    rc = log_tail(lines=20, level="ERROR")
    assert rc == 0
    out = capsys.readouterr().out
    assert "smtp connection refused" in out
    assert "check started" not in out


def test_log_tail_filter_info(log_file, capsys, monkeypatch):
    monkeypatch.setattr("fim.observe._LOG_PATH", log_file)
    log_tail(lines=20, level="INFO")
    out = capsys.readouterr().out
    assert "DEBUG" not in out
    assert "ERROR" not in out
    assert "check started" in out


def test_log_tail_filter_no_matches(log_file, capsys, monkeypatch):
    monkeypatch.setattr("fim.observe._LOG_PATH", log_file)
    log_tail(lines=20, level="CRITICAL")
    out = capsys.readouterr().out
    assert "no CRITICAL log entries" in out


def test_log_tail_file_not_found(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("fim.observe._LOG_PATH", tmp_path / "nonexistent.log")
    rc = log_tail(lines=20, level=None)
    assert rc == 1
    assert "not found" in capsys.readouterr().err


def test_log_tail_unreadable_file(tmp_path, capsys, monkeypatch):
    log_file = tmp_path / "check.log"
    log_file.write_text("data", encoding="utf-8")
    monkeypatch.setattr("fim.observe._LOG_PATH", log_file)
    real_open = builtins.open

    def _raise(path, *a, **kw):
        if Path(path) == log_file:
            raise OSError("permission denied")
        return real_open(path, *a, **kw)

    with patch("builtins.open", side_effect=_raise):
        rc = log_tail(lines=20, level=None)
    assert rc == 1
    assert "Cannot read" in capsys.readouterr().err


def test_log_tail_empty_file(tmp_path, capsys, monkeypatch):
    log_file = tmp_path / "check.log"
    log_file.write_text("", encoding="utf-8")
    monkeypatch.setattr("fim.observe._LOG_PATH", log_file)
    log_tail(lines=20, level=None)
    assert "no log entries" in capsys.readouterr().out
