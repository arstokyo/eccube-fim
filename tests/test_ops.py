import subprocess
import pytest
from fim.config import Config, NotifyEmail, NotifySlack
from fim.ops import approve_change


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


def test_approve_change_returns_false_on_no_diff(ops_cfg, capsys):
    result = approve_change(ops_cfg, "index.twig", confirm_fn=lambda: "y")
    assert result is False
    assert "No uncommitted changes" in capsys.readouterr().out


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
