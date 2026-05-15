import pytest
from fim.config import load_config, Config, NotifyEmail, NotifySlack, DEFAULT_SUPPRESS_HOURS
from fim.exceptions import FimConfigError


def _write_yaml(path, content):
    path.write_text(content, encoding="utf-8")


def _write_minimal_configs(d, root_path="/var/www/html"):
    _write_yaml(d / "daemon.yaml", f"root_path: {root_path}\n")
    _write_yaml(d / "targets.yaml", "target_files:\n  - index.twig\n")
    _write_yaml(d / "notify.yaml", "email:\n  smtp_host: smtp.example.com\n")


def test_load_config_minimal(tmp_path):
    _write_minimal_configs(tmp_path)
    cfg = load_config(str(tmp_path))
    assert cfg.root_path == "/var/www/html"
    assert cfg.target_files == ["index.twig"]
    assert cfg.email.smtp_host == "smtp.example.com"
    assert cfg.suppress_window_hours == DEFAULT_SUPPRESS_HOURS


def test_load_config_full(tmp_path):
    _write_yaml(tmp_path / "daemon.yaml", (
        "root_path: /var/www\n"
        "state_db: /tmp/state.db\n"
        "heartbeat:\n  enabled: false\n  file: /tmp/hb\n"
    ))
    _write_yaml(tmp_path / "targets.yaml", (
        "deduplication:\n  suppress_window_hours: 3\n"
        "target_files:\n  - a.twig\n  - b.twig\n"
    ))
    _write_yaml(tmp_path / "notify.yaml", (
        "email:\n  smtp_host: smtp.test.com\n  smtp_port: 465\n"
        "  smtp_user: u\n  recipients:\n    - x@y.com\n"
        "slack:\n  enabled: true\n  webhook_url_files:\n    - /tmp/wh\n"
    ))
    cfg = load_config(str(tmp_path))
    assert cfg.suppress_window_hours == 3
    assert cfg.state_db == "/tmp/state.db"
    assert cfg.heartbeat_enabled is False
    assert cfg.heartbeat_file == "/tmp/hb"
    assert cfg.target_files == ["a.twig", "b.twig"]
    assert cfg.email.smtp_port == 465
    assert cfg.slack.enabled is True
    assert cfg.slack.webhook_url_files == ["/tmp/wh"]


def test_missing_daemon_yaml(tmp_path):
    _write_yaml(tmp_path / "targets.yaml", "target_files:\n  - index.twig\n")
    _write_yaml(tmp_path / "notify.yaml", "email:\n  smtp_host: smtp.example.com\n")
    with pytest.raises(FimConfigError, match="daemon.yaml"):
        load_config(str(tmp_path))


def test_missing_root_path(tmp_path):
    _write_yaml(tmp_path / "daemon.yaml", "state_db: /tmp/s.db\n")
    _write_yaml(tmp_path / "targets.yaml", "target_files:\n  - index.twig\n")
    _write_yaml(tmp_path / "notify.yaml", "email:\n  smtp_host: smtp.example.com\n")
    with pytest.raises(FimConfigError, match="root_path"):
        load_config(str(tmp_path))


def test_empty_target_files(tmp_path):
    _write_yaml(tmp_path / "daemon.yaml", "root_path: /var/www\n")
    _write_yaml(tmp_path / "targets.yaml", "target_files: []\n")
    _write_yaml(tmp_path / "notify.yaml", "email:\n  smtp_host: smtp.example.com\n")
    with pytest.raises(FimConfigError, match="target_files"):
        load_config(str(tmp_path))


def test_missing_smtp_host(tmp_path):
    _write_yaml(tmp_path / "daemon.yaml", "root_path: /var/www\n")
    _write_yaml(tmp_path / "targets.yaml", "target_files:\n  - index.twig\n")
    _write_yaml(tmp_path / "notify.yaml", "email:\n  smtp_port: 587\n")
    with pytest.raises(FimConfigError, match="smtp_host"):
        load_config(str(tmp_path))
