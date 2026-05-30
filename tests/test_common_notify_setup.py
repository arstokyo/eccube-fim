import pytest
import yaml

from common.notify_setup import (
    setup_notify_interactive,
    _ask_yes_no,
    _prompt,
    _validate_email,
)


def _ok(_config_dir: str) -> int:
    return 0


# ---------------------------------------------------------------------------
# _ask_yes_no / _prompt
# ---------------------------------------------------------------------------

def test_ask_yes_no_default_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert _ask_yes_no("Q", default_yes=True) is True


def test_ask_yes_no_default_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert _ask_yes_no("Q", default_yes=False) is False


def test_prompt_returns_default_on_empty(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert _prompt("Label", default="fallback") == "fallback"


def test_validate_email_rejects_bad():
    with pytest.raises(ValueError, match="Invalid email address"):
        _validate_email("notanemail")


# ---------------------------------------------------------------------------
# setup_notify_interactive — TTY guard
# ---------------------------------------------------------------------------

def test_no_tty_returns_1(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert setup_notify_interactive(str(tmp_path), _ok) == 1


# ---------------------------------------------------------------------------
# setup_notify_interactive — both channels disabled
# ---------------------------------------------------------------------------

def test_both_disabled_writes_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    answers = iter(["n", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    rc = setup_notify_interactive(str(tmp_path), _ok)
    assert rc == 0
    data = yaml.safe_load((tmp_path / "notify.yaml").read_text(encoding="utf-8"))
    assert data["email"]["enabled"] is False
    assert data["slack"]["enabled"] is False


def test_validate_fn_return_is_propagated(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    answers = iter(["n", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert setup_notify_interactive(str(tmp_path), lambda _c: 1) == 1


# ---------------------------------------------------------------------------
# setup_notify_interactive — email enabled writes a 0600 secret + config
# ---------------------------------------------------------------------------

def test_email_enabled_writes_secret(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    answers = iter([
        "y",                  # enable email
        "smtp.example.com",   # smtp_host
        "587",                # smtp_port
        "user@example.com",   # smtp_user
        "fim@example.com",    # from
        "ops@example.com",    # recipients
        "n",                  # disable slack
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _: "secret")
    rc = setup_notify_interactive(str(tmp_path), _ok)
    assert rc == 0
    data = yaml.safe_load((tmp_path / "notify.yaml").read_text(encoding="utf-8"))
    assert data["email"]["enabled"] is True
    assert data["email"]["smtp_host"] == "smtp.example.com"
    assert data["email"]["smtp_port"] == 587
    pw = tmp_path / "smtp.password"
    assert pw.read_text(encoding="utf-8") == "secret"
    assert oct(pw.stat().st_mode)[-3:] == "600"


# ---------------------------------------------------------------------------
# setup_notify_interactive — slack enabled writes a 0600 webhook file
# ---------------------------------------------------------------------------

def test_slack_enabled_writes_webhook(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    answers = iter([
        "n",                              # disable email
        "y",                              # enable slack
        "https://hooks.slack.test/abc",   # webhook 1
        "",                               # stop adding webhooks
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    rc = setup_notify_interactive(str(tmp_path), _ok)
    assert rc == 0
    data = yaml.safe_load((tmp_path / "notify.yaml").read_text(encoding="utf-8"))
    assert data["slack"]["enabled"] is True
    assert data["slack"]["webhook_url_files"] == [str(tmp_path / "slack-1.webhook")]
    wh = tmp_path / "slack-1.webhook"
    assert wh.read_text(encoding="utf-8") == "https://hooks.slack.test/abc"
    assert oct(wh.stat().st_mode)[-3:] == "600"


# ---------------------------------------------------------------------------
# setup_notify_interactive — existing config is read for status display
# ---------------------------------------------------------------------------

def test_reads_existing_config(tmp_path, monkeypatch):
    (tmp_path / "notify.yaml").write_text(
        yaml.dump({"email": {"enabled": False}, "slack": {"enabled": False}}),
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    answers = iter(["n", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert setup_notify_interactive(str(tmp_path), _ok) == 0
