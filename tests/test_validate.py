import subprocess
import pytest
from fim.config import Config, NotifyEmail, NotifySlack
from fim.validate import validate_config, send_test_mail, send_test_slack


@pytest.fixture
def email_cfg():
    return NotifyEmail(
        smtp_host="smtp.example.test",
        smtp_port=587,
        from_addr="fim@example.test",
        recipients=["ops@example.test"],
    )


@pytest.fixture
def diag_cfg(repo, email_cfg):
    twig = repo / "index.twig"
    twig.write_text("")
    subprocess.run(["git", "add", "index.twig"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add twig"], cwd=repo, check=True, capture_output=True)
    return Config(
        root_path=str(repo),
        target_files=["index.twig"],
        email=email_cfg,
        slack=NotifySlack(),
        heartbeat_enabled=False,
    )


def test_send_test_mail_returns_1_when_channel_returns_false(monkeypatch, diag_cfg, capsys):
    monkeypatch.setattr("fim.validate.send_test_notification",
                        lambda cfg, h, channel_name=None: {"EmailChannel": False})
    assert send_test_mail(diag_cfg) == 1
    assert "FAILED" in capsys.readouterr().err


def test_send_test_mail_returns_0_on_success(monkeypatch, diag_cfg, capsys):
    monkeypatch.setattr("fim.validate.send_test_notification",
                        lambda cfg, h, channel_name=None: {"EmailChannel": True})
    assert send_test_mail(diag_cfg) == 0
    assert "Test email sent successfully" in capsys.readouterr().out


def test_send_test_mail_returns_1_on_exception(monkeypatch, diag_cfg):
    def _raise(cfg, h, channel_name=None):
        raise OSError("connection refused")
    monkeypatch.setattr("fim.validate.send_test_notification", _raise)
    assert send_test_mail(diag_cfg) == 1


def test_send_test_slack_disabled_returns_1(diag_cfg, capsys):
    # slack is disabled by default in diag_cfg (NotifySlack())
    assert send_test_slack(diag_cfg) == 1
    assert "disabled" in capsys.readouterr().err


def test_send_test_slack_returns_0_on_success(monkeypatch, diag_cfg, capsys):
    diag_cfg.slack.enabled = True
    diag_cfg.slack.webhook_url_files = ["/tmp/fake_webhook"]
    monkeypatch.setattr("fim.validate.send_test_notification",
                        lambda cfg, h, channel_name=None: {"SlackChannel": True})
    assert send_test_slack(diag_cfg) == 0
    assert "Test Slack message sent successfully" in capsys.readouterr().out


def test_send_test_slack_returns_1_on_failure(monkeypatch, diag_cfg, capsys):
    diag_cfg.slack.enabled = True
    diag_cfg.slack.webhook_url_files = ["/tmp/fake_webhook"]
    monkeypatch.setattr("fim.validate.send_test_notification",
                        lambda cfg, h, channel_name=None: {"SlackChannel": False})
    assert send_test_slack(diag_cfg) == 1
    assert "FAILED" in capsys.readouterr().err


def test_send_test_mail_passes_email_channel_name(monkeypatch, diag_cfg):
    """send_test_mail must forward channel_name='email' to send_test_notification."""
    captured = {}

    def fake_notify(cfg, hostname, channel_name=None):
        captured["channel_name"] = channel_name
        return {"EmailChannel": True}

    monkeypatch.setattr("fim.validate.send_test_notification", fake_notify)
    send_test_mail(diag_cfg)

    assert captured["channel_name"] == "email"


def test_send_test_slack_passes_slack_channel_name(monkeypatch, diag_cfg):
    """send_test_slack must forward channel_name='slack' to send_test_notification."""
    diag_cfg.slack.enabled = True
    diag_cfg.slack.webhook_url_files = ["/tmp/fake_webhook"]
    captured = {}

    def fake_notify(cfg, hostname, channel_name=None):
        captured["channel_name"] = channel_name
        return {"SlackChannel": True}

    monkeypatch.setattr("fim.validate.send_test_notification", fake_notify)
    send_test_slack(diag_cfg)

    assert captured["channel_name"] == "slack"


def test_validate_config_passes_for_existing_root(diag_cfg, capsys):
    result = validate_config(diag_cfg)
    assert "Config validation" in capsys.readouterr().out
    assert result is True


def test_validate_config_fails_for_missing_root(diag_cfg, capsys):
    diag_cfg.root_path = "/nonexistent/path"
    result = validate_config(diag_cfg)
    assert "NOT FOUND" in capsys.readouterr().out
    assert result is False
