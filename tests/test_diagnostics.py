import pytest
from fim.config import Config, NotifyEmail, NotifySlack
from fim.diagnostics import validate_config, send_test_mail


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
    return Config(
        root_path=str(repo),
        target_files=["index.twig"],
        email=email_cfg,
        slack=NotifySlack(),
        heartbeat_enabled=False,
    )


def test_send_test_mail_returns_1_when_channel_returns_false(monkeypatch, diag_cfg, capsys):
    monkeypatch.setattr("fim.diagnostics.EmailChannel.send", lambda self, h, ds: False)
    assert send_test_mail(diag_cfg) == 1
    assert "FAILED" in capsys.readouterr().err


def test_send_test_mail_returns_0_on_success(monkeypatch, diag_cfg, capsys):
    monkeypatch.setattr("fim.diagnostics.EmailChannel.send", lambda self, h, ds: True)
    assert send_test_mail(diag_cfg) == 0
    assert "Test email sent successfully" in capsys.readouterr().out


def test_send_test_mail_returns_1_on_exception(monkeypatch, diag_cfg):
    def _raise(self, h, ds):
        raise OSError("connection refused")
    monkeypatch.setattr("fim.diagnostics.EmailChannel.send", _raise)
    assert send_test_mail(diag_cfg) == 1


def test_validate_config_passes_for_existing_root(diag_cfg, capsys):
    result = validate_config(diag_cfg)
    assert "Config validation" in capsys.readouterr().out
    assert isinstance(result, bool)


def test_validate_config_fails_for_missing_root(diag_cfg, capsys):
    diag_cfg.root_path = "/nonexistent/path"
    result = validate_config(diag_cfg)
    assert "NOT FOUND" in capsys.readouterr().out
