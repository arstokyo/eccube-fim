import sqlite3
from unittest.mock import patch

import pytest

from fim.config import Config, NotifyEmail, NotifySlack
from fim.observe import db_list, db_clear


@pytest.fixture
def cfg(tmp_path):
    db = tmp_path / "state.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE notifications "
        "(file_path TEXT, content_sha256 TEXT, last_notified_at INTEGER, "
        "PRIMARY KEY (file_path, content_sha256))"
    )
    conn.execute("INSERT INTO notifications VALUES ('a.twig', 'aabbcc', 1716000000)")
    conn.execute("INSERT INTO notifications VALUES ('b.twig', 'ddeeff', 1716000100)")
    conn.commit()
    conn.close()
    return Config(
        root_path="/tmp/repo",
        target_files=["a.twig"],
        email=NotifyEmail(smtp_host="smtp.x.com", from_addr="a@b.com", recipients=["a@b.com"]),
        slack=NotifySlack(),
        state_db=str(db),
    )


def test_db_list_shows_all_records(cfg, capsys):
    rc = db_list(cfg)
    out = capsys.readouterr().out
    assert rc == 0
    assert "a.twig" in out
    assert "b.twig" in out
    assert "2 record(s)" in out


def test_db_list_empty(cfg, tmp_path, capsys):
    db = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE notifications "
        "(file_path TEXT, content_sha256 TEXT, last_notified_at INTEGER)"
    )
    conn.commit()
    conn.close()
    cfg.state_db = str(db)
    rc = db_list(cfg)
    assert rc == 0
    assert "No suppressed" in capsys.readouterr().out


def test_db_list_bad_db(cfg, capsys):
    cfg.state_db = "/nonexistent/state.db"
    rc = db_list(cfg)
    assert rc == 1
    assert "Cannot read" in capsys.readouterr().err


def test_db_clear_all_with_yes(cfg, capsys):
    rc = db_clear(cfg, file_path=None, yes=True)
    assert rc == 0
    assert "Removed 2 records" in capsys.readouterr().out
    conn = sqlite3.connect(cfg.state_db)
    count = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
    conn.close()
    assert count == 0


def test_db_clear_single_file_with_yes(cfg, capsys):
    rc = db_clear(cfg, file_path="a.twig", yes=True)
    assert rc == 0
    assert "Removed 1 record" in capsys.readouterr().out
    conn = sqlite3.connect(cfg.state_db)
    row = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE file_path='a.twig'"
    ).fetchone()
    conn.close()
    assert row[0] == 0


def test_db_clear_preserves_other_records(cfg):
    db_clear(cfg, file_path="a.twig", yes=True)
    conn = sqlite3.connect(cfg.state_db)
    count = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
    conn.close()
    assert count == 1  # b.twig still present


def test_db_clear_aborted_without_yes(cfg, capsys):
    with patch("builtins.input", return_value="n"):
        rc = db_clear(cfg, file_path=None, yes=False)
    assert rc == 0
    assert "Aborted" in capsys.readouterr().out
    conn = sqlite3.connect(cfg.state_db)
    count = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
    conn.close()
    assert count == 2  # nothing deleted


def test_db_clear_confirmed_interactively(cfg, capsys):
    with patch("builtins.input", return_value="y"):
        rc = db_clear(cfg, file_path=None, yes=False)
    assert rc == 0
    assert "Removed" in capsys.readouterr().out


def test_db_clear_bad_db(cfg, capsys):
    cfg.state_db = "/nonexistent/state.db"
    rc = db_clear(cfg, file_path=None, yes=True)
    assert rc == 1
    assert "Cannot clear" in capsys.readouterr().err


def test_db_clear_nonexistent_file_path_removes_zero(cfg, capsys):
    rc = db_clear(cfg, file_path="no_such_file.twig", yes=True)
    assert rc == 0
    assert "Removed 0" in capsys.readouterr().out
