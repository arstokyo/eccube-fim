import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fim.config import Config, NotifyEmail, NotifySlack
from fim import observe
from fim.utils import JST


@pytest.fixture
def cfg(tmp_path):
    db = tmp_path / "state.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE notifications "
        "(file_path TEXT, content_sha256 TEXT, last_notified_at INTEGER)"
    )
    conn.execute("INSERT INTO notifications VALUES ('a.twig', 'abc', 1)")
    conn.commit()
    conn.close()
    return Config(
        root_path="/tmp/repo",
        target_files=["a.twig"],
        email=NotifyEmail(smtp_host="smtp.x.com", from_addr="a@b.com", recipients=["a@b.com"]),
        slack=NotifySlack(),
        state_db=str(db),
        heartbeat_enabled=True,
        heartbeat_file=str(tmp_path / "heartbeat"),
    )


def _systemctl_mock(state: str = "active") -> MagicMock:
    now_usec = int(datetime.now(JST).timestamp() * 1_000_000)
    next_usec = now_usec + 120 * 1_000_000

    def _side(cmd, **kw):
        m = MagicMock()
        m.stdout = (state if "is-active" in cmd else str(next_usec)) + "\n"
        return m

    return _side


def test_status_runs_without_error(cfg, capsys):
    with patch("fim.observe.subprocess.run", side_effect=_systemctl_mock()):
        with patch("os.path.getmtime", return_value=datetime.now(JST).timestamp() - 30):
            rc = observe.status(cfg)
    assert rc == 0
    out = capsys.readouterr().out
    assert "eccube-fim status" in out
    assert "Service" in out
    assert "Heartbeat" in out
    assert "DB records" in out


def test_status_shows_timer_state(cfg, capsys):
    with patch("fim.observe.subprocess.run", side_effect=_systemctl_mock("active")):
        with patch("os.path.getmtime", return_value=datetime.now(JST).timestamp() - 30):
            observe.status(cfg)
    assert "active" in capsys.readouterr().out


def test_status_systemd_not_available(cfg, capsys):
    with patch("fim.observe.subprocess.run", side_effect=OSError):
        observe.status(cfg)
    assert "systemd not available" in capsys.readouterr().out


def test_status_heartbeat_absent(cfg, capsys):
    with patch("fim.observe.subprocess.run", side_effect=_systemctl_mock()):
        observe.status(cfg)
    assert "not found" in capsys.readouterr().out


def test_status_heartbeat_stale(cfg, capsys):
    stale = datetime.now(JST).timestamp() - 700  # > 10 min
    with patch("fim.observe.subprocess.run", side_effect=_systemctl_mock()):
        with patch("os.path.getmtime", return_value=stale):
            observe.status(cfg)
    assert "STALE" in capsys.readouterr().out


def test_status_heartbeat_ok(cfg, capsys):
    fresh = datetime.now(JST).timestamp() - 30
    with patch("fim.observe.subprocess.run", side_effect=_systemctl_mock()):
        with patch("os.path.getmtime", return_value=fresh):
            observe.status(cfg)
    assert "OK" in capsys.readouterr().out


def test_status_db_count(cfg, capsys):
    with patch("fim.observe.subprocess.run", side_effect=_systemctl_mock()):
        with patch("os.path.getmtime", return_value=datetime.now(JST).timestamp() - 30):
            observe.status(cfg)
    assert "1 suppressed file" in capsys.readouterr().out


def test_status_heartbeat_disabled(cfg, capsys):
    cfg.heartbeat_enabled = False
    with patch("fim.observe.subprocess.run", side_effect=_systemctl_mock()):
        observe.status(cfg)
    assert "disabled" in capsys.readouterr().out


def test_status_log_not_found(cfg, capsys, monkeypatch):
    monkeypatch.setattr("fim.observe._LOG_PATH", Path("/nonexistent/check.log"))
    with patch("fim.observe.subprocess.run", side_effect=_systemctl_mock()):
        with patch("os.path.getmtime", return_value=datetime.now(JST).timestamp() - 30):
            observe.status(cfg)
    assert "log file not found" in capsys.readouterr().out


def test_status_last_error_from_log(cfg, tmp_path, capsys, monkeypatch):
    log_file = tmp_path / "check.log"
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    log_file.write_text(
        f"{now_str} INFO check completed\n"
        f"{now_str} ERROR smtp connection failed\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("fim.observe._LOG_PATH", log_file)
    with patch("fim.observe.subprocess.run", side_effect=_systemctl_mock()):
        with patch("os.path.getmtime", return_value=datetime.now(JST).timestamp() - 30):
            observe.status(cfg)
    assert "smtp connection failed" in capsys.readouterr().out


def test_status_no_recent_error(cfg, tmp_path, capsys, monkeypatch):
    log_file = tmp_path / "check.log"
    # ERROR line is >24h old — should not show up
    old_str = "2020-01-01 00:00:00"
    log_file.write_text(f"{old_str} ERROR old error\n", encoding="utf-8")
    monkeypatch.setattr("fim.observe._LOG_PATH", log_file)
    with patch("fim.observe.subprocess.run", side_effect=_systemctl_mock()):
        with patch("os.path.getmtime", return_value=datetime.now(JST).timestamp() - 30):
            observe.status(cfg)
    assert "none in last 24h" in capsys.readouterr().out
