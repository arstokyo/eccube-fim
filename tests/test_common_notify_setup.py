import yaml
import pytest

from common.notify_setup import setup_notify_interactive, _ask, _yes_no


# ---------------------------------------------------------------------------
# _ask — returns input or default
# ---------------------------------------------------------------------------

def test_ask_returns_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "myvalue")
    assert _ask("prompt", "default") == "myvalue"


def test_ask_returns_default_on_empty(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert _ask("prompt", "default") == "default"


# ---------------------------------------------------------------------------
# _yes_no
# ---------------------------------------------------------------------------

def test_yes_no_y_returns_true(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert _yes_no("prompt", False) is True


def test_yes_no_n_returns_false(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert _yes_no("prompt", True) is False


def test_yes_no_empty_returns_default_true(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert _yes_no("prompt", True) is True


def test_yes_no_empty_returns_default_false(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert _yes_no("prompt", False) is False


# ---------------------------------------------------------------------------
# setup_notify_interactive — email disabled
# ---------------------------------------------------------------------------

def test_setup_notify_email_disabled(tmp_path, monkeypatch):
    answers = iter(["n", "n"])  # email=no, slack=no
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    rc = setup_notify_interactive(str(tmp_path))
    assert rc == 0
    data = yaml.safe_load((tmp_path / "notify.yaml").read_text(encoding="utf-8"))
    assert data["email"]["enabled"] is False
    assert data["slack"]["enabled"] is False


# ---------------------------------------------------------------------------
# setup_notify_interactive — email enabled
# ---------------------------------------------------------------------------

def test_setup_notify_email_enabled(tmp_path, monkeypatch):
    answers = iter([
        "y",                   # enable email
        "smtp.example.com",    # smtp_host
        "587",                 # smtp_port
        "user@example.com",    # smtp_user
        "/etc/eccube-fim/smtp.password",  # password file
        "fim@example.com",     # from
        "admin@example.com",   # recipients[0]
        "n",                   # disable slack
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    rc = setup_notify_interactive(str(tmp_path))
    assert rc == 0
    data = yaml.safe_load((tmp_path / "notify.yaml").read_text(encoding="utf-8"))
    assert data["email"]["enabled"] is True
    assert data["email"]["smtp_host"] == "smtp.example.com"
    assert data["email"]["smtp_port"] == 587


# ---------------------------------------------------------------------------
# setup_notify_interactive — slack enabled
# ---------------------------------------------------------------------------

def test_setup_notify_slack_enabled(tmp_path, monkeypatch):
    answers = iter([
        "n",                                  # disable email
        "y",                                  # enable slack
        "/etc/eccube-fim/slack.webhook",      # webhook file
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    rc = setup_notify_interactive(str(tmp_path))
    assert rc == 0
    data = yaml.safe_load((tmp_path / "notify.yaml").read_text(encoding="utf-8"))
    assert data["slack"]["enabled"] is True
    assert data["slack"]["webhook_url_files"][0] == "/etc/eccube-fim/slack.webhook"


# ---------------------------------------------------------------------------
# setup_notify_interactive — existing config is pre-filled (reads current)
# ---------------------------------------------------------------------------

def test_setup_notify_reads_existing(tmp_path, monkeypatch):
    existing = {
        "email": {"enabled": False},
        "slack": {"enabled": False},
    }
    (tmp_path / "notify.yaml").write_text(
        yaml.dump(existing, allow_unicode=True), encoding="utf-8"
    )
    answers = iter(["n", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    rc = setup_notify_interactive(str(tmp_path))
    assert rc == 0


# ---------------------------------------------------------------------------
# setup_notify_interactive — write error returns 1
# ---------------------------------------------------------------------------

def test_setup_notify_write_error_returns_1(tmp_path, monkeypatch, capsys):
    answers = iter(["n", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    from unittest.mock import patch
    with patch("common.notify_setup.Path.write_text",
               side_effect=OSError("permission denied")):
        rc = setup_notify_interactive(str(tmp_path))
    assert rc == 1
    assert "Error" in capsys.readouterr().err
