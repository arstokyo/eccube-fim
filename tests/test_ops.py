import subprocess
import pytest
from fim.config import Config, NotifyEmail, NotifySlack
from fim.ops import send_test_mail, validate_config, approve_change


@pytest.fixture
def email_cfg():
    return NotifyEmail(
        smtp_host="smtp.example.test",
        smtp_port=587,
        from_addr="fim@example.test",
        recipients=["ops@example.test"],
    )


@pytest.fixture
def ops_cfg(repo, email_cfg):
    return Config(
        root_path=str(repo),
        target_files=["index.twig"],
        email=email_cfg,
        slack=NotifySlack(),
        heartbeat_enabled=False,
    )


def test_send_test_mail_returns_1_when_channel_returns_false(monkeypatch, ops_cfg, capsys):
    monkeypatch.setattr("fim.ops.EmailChannel.send", lambda self, hostname, d: False)
    result = send_test_mail(ops_cfg)
    assert result == 1
    captured = capsys.readouterr()
    assert "FAILED" in captured.err
    assert "Test email sent successfully" not in captured.out


def test_send_test_mail_returns_0_on_success(monkeypatch, ops_cfg, capsys):
    monkeypatch.setattr("fim.ops.EmailChannel.send", lambda self, hostname, d: True)
    result = send_test_mail(ops_cfg)
    assert result == 0
    captured = capsys.readouterr()
    assert "Test email sent successfully" in captured.out


def test_send_test_mail_returns_1_on_exception(monkeypatch, ops_cfg, capsys):
    def raise_exc(self, hostname, d):
        raise OSError("connection refused")
    monkeypatch.setattr("fim.ops.EmailChannel.send", raise_exc)
    result = send_test_mail(ops_cfg)
    assert result == 1


def test_validate_config_passes_for_existing_root(ops_cfg, capsys):
    result = validate_config(ops_cfg)
    captured = capsys.readouterr()
    assert "Config validation" in captured.out
    assert isinstance(result, bool)


def test_validate_config_fails_for_missing_root(ops_cfg, capsys):
    ops_cfg.root_path = "/nonexistent/path"
    result = validate_config(ops_cfg)
    captured = capsys.readouterr()
    assert "NOT FOUND" in captured.out


def test_approve_change_returns_false_on_no_diff(ops_cfg, capsys):
    result = approve_change(ops_cfg, "index.twig", confirm_fn=lambda: "y")
    assert result is False
    captured = capsys.readouterr()
    assert "No uncommitted changes" in captured.out


def test_approve_change_returns_false_on_cancel(ops_cfg, repo):
    (repo / "index.twig").write_text("original\n")
    subprocess.run(["git", "add", "index.twig"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True)
    (repo / "index.twig").write_text("changed\n")
    result = approve_change(ops_cfg, "index.twig", confirm_fn=lambda: "n")
    assert result is False


def test_approve_change_commits_on_confirm(ops_cfg, repo):
    (repo / "index.twig").write_text("original\n")
    subprocess.run(["git", "add", "index.twig"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True)
    (repo / "index.twig").write_text("approved change\n")
    result = approve_change(ops_cfg, "index.twig", message="legitimate update",
                            confirm_fn=lambda: "y")
    assert result is True
    log = subprocess.check_output(
        ["git", "log", "--oneline", "-1"], cwd=repo, text=True
    )
    assert "FIM-approved" in log
