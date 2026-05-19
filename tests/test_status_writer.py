import json
import logging
import os
from pathlib import Path

import pytest

from fim.status_writer import write_status, _heartbeat_info, _get_db_data, _timer_interval_secs


@pytest.fixture()
def cfg(tmp_path):
    from fim.config import Config, NotifyEmail, NotifySlack
    db_path = str(tmp_path / "state.db")
    hb_path = str(tmp_path / "heartbeat")
    Path(hb_path).touch()
    return Config(
        root_path=str(tmp_path),
        target_files=["app/template/default/Shopping/index.twig"],
        email=NotifyEmail(smtp_host="smtp.example.com", from_addr="a@b.com"),
        slack=NotifySlack(),
        state_db=db_path,
        heartbeat_file=hb_path,
    )


def test_write_status_creates_json(tmp_path, cfg, monkeypatch):
    status_file = tmp_path / "status.json"
    monkeypatch.setattr("fim.status_writer.INSTALL_STATUS_DIR", str(tmp_path))
    monkeypatch.setattr("fim.status_writer.INSTALL_STATUS_FILE", str(status_file))

    write_status(cfg)

    assert status_file.exists()
    data = json.loads(status_file.read_text())
    assert data["schema_version"] == 1
    assert "generated_at" in data
    assert "timer_interval_secs" in data
    assert "heartbeat" in data
    assert "recent_detections" in data
    assert "recent_log" in data


def test_write_status_file_mode_644(tmp_path, cfg, monkeypatch):
    status_file = tmp_path / "status.json"
    monkeypatch.setattr("fim.status_writer.INSTALL_STATUS_DIR", str(tmp_path))
    monkeypatch.setattr("fim.status_writer.INSTALL_STATUS_FILE", str(status_file))

    write_status(cfg)

    mode = oct(os.stat(status_file).st_mode)[-3:]
    assert mode == "644"


def test_timer_interval_secs_reads_unit(tmp_path, monkeypatch):
    timer = tmp_path / "eccube-fim-check.timer"
    timer.write_text("[Timer]\nOnCalendar=*:0/15\n")
    monkeypatch.setattr("fim.status_writer.INSTALL_SYSTEMD_DIR", str(tmp_path))
    assert _timer_interval_secs() == 15 * 60


def test_timer_interval_secs_fallback_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("fim.status_writer.INSTALL_SYSTEMD_DIR", str(tmp_path))
    assert _timer_interval_secs() == 15 * 60   # default fallback


def test_heartbeat_info_ok(tmp_path, cfg):
    info = _heartbeat_info(cfg, interval_secs=900)
    assert info["enabled"] is True
    assert info["health"] == "OK"
    assert info["age_seconds"] >= 0


def test_heartbeat_info_stale_uses_interval(tmp_path, cfg):
    # interval_secs=0 → stale_threshold=0; any age (even ~0) exceeds it → STALE
    info = _heartbeat_info(cfg, interval_secs=0)
    assert info["health"] == "STALE"


def test_heartbeat_info_not_found(cfg):
    cfg.heartbeat_file = "/nonexistent/path/heartbeat"
    info = _heartbeat_info(cfg, interval_secs=900)
    assert info["health"] == "NOT_FOUND"


def test_heartbeat_info_disabled(cfg):
    cfg.heartbeat_enabled = False
    info = _heartbeat_info(cfg, interval_secs=900)
    assert info == {"enabled": False}


def test_get_db_data_empty(cfg):
    count, detections = _get_db_data(cfg)
    assert count == 0
    assert detections == []


def test_get_db_data_bad_path_warns(cfg, caplog):
    cfg.state_db = "/nonexistent/state.db"
    with caplog.at_level(logging.WARNING, logger="fim.status_writer"):
        count, detections = _get_db_data(cfg)
    assert count == -1
    assert detections == []
    assert any("Cannot read state DB" in r.message for r in caplog.records)


def test_write_status_os_error_is_warned(tmp_path, cfg, monkeypatch, caplog):
    monkeypatch.setattr("fim.status_writer.INSTALL_STATUS_DIR", "/nonexistent/readonly/path")
    monkeypatch.setattr("fim.status_writer.INSTALL_STATUS_FILE", "/nonexistent/readonly/path/s.json")

    with caplog.at_level(logging.WARNING, logger="fim.status_writer"):
        write_status(cfg)   # must not raise

    assert any("Cannot write status file" in r.message for r in caplog.records)


def test_write_status_atomic(tmp_path, cfg, monkeypatch):
    status_file = tmp_path / "status.json"
    monkeypatch.setattr("fim.status_writer.INSTALL_STATUS_DIR", str(tmp_path))
    monkeypatch.setattr("fim.status_writer.INSTALL_STATUS_FILE", str(status_file))

    write_status(cfg)
    # .tmp file must not remain after successful write
    assert not (tmp_path / "status.tmp").exists()
