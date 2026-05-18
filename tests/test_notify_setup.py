import os
import pytest
import yaml
from unittest.mock import patch

from fim.notify_setup import (
    _secure_write,
    _load_raw_notify,
    _print_notify_status,
    _ask_yes_no,
    _prompt,
    setup_notify_interactive,
)


def test_secure_write_creates_with_mode_600(tmp_path):
    p = tmp_path / "secret.txt"
    _secure_write(str(p), "hunter2")
    assert p.read_text() == "hunter2"
    assert oct(p.stat().st_mode)[-3:] == "600"


def test_secure_write_overwrites_existing(tmp_path):
    p = tmp_path / "secret.txt"
    p.write_text("old")
    _secure_write(str(p), "new")
    assert p.read_text() == "new"


def test_load_raw_notify_missing_returns_defaults(tmp_path):
    data = _load_raw_notify(str(tmp_path / "notify.yaml"))
    assert data["email"]["enabled"] is False
    assert data["slack"]["enabled"] is False


def test_load_raw_notify_reads_existing(tmp_path):
    f = tmp_path / "notify.yaml"
    f.write_text("email:\n  enabled: true\nslack:\n  enabled: false\n")
    data = _load_raw_notify(str(f))
    assert data["email"]["enabled"] is True


def test_print_notify_status_no_crash(capsys):
    _print_notify_status({"email": {"enabled": True}, "slack": {"enabled": False}})
    out = capsys.readouterr().out
    assert "enabled" in out
    assert "disabled" in out


def test_ask_yes_no_default_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert _ask_yes_no("Configure?", default_yes=False) is False


def test_ask_yes_no_explicit_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert _ask_yes_no("Configure?") is True


def test_prompt_returns_default_on_empty(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert _prompt("Label", default="fallback") == "fallback"


def test_setup_notify_no_tty_exits_1(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert setup_notify_interactive(str(tmp_path)) == 1


def test_setup_notify_no_changes_writes_yaml(tmp_path, monkeypatch):
    (tmp_path / "daemon.yaml").write_text(
        "root_path: /tmp\nstate_db: /tmp/state.db\n"
        "heartbeat:\n  enabled: false\n  file: /tmp/hb\n"
    )
    (tmp_path / "targets.yaml").write_text(
        "target_files:\n  - app/template/default/Shopping/index.twig\n"
    )
    # email must be enabled so load_config() passes the "at least one channel" guard
    (tmp_path / "notify.yaml").write_text(
        "email:\n  enabled: true\n  smtp_host: smtp.test\n"
        "  from: fim@test\n  recipients: [ops@test]\n"
        "slack:\n  enabled: false\n"
    )
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    responses = iter(["n", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    with patch("fim.notify_setup.validate_config", return_value=True):
        result = setup_notify_interactive(str(tmp_path))
    assert result == 0
    data = yaml.safe_load((tmp_path / "notify.yaml").read_text())
    assert data["email"]["enabled"] is True
    assert data["slack"]["enabled"] is False
