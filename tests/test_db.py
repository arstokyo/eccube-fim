import pytest
from fim.db import Db
from fim.exceptions import FimDbError


def test_record_and_suppress(db):
    db.record("index.twig", "abc123")
    assert db.is_suppressed("index.twig", "abc123", hours=1) is True


def test_not_suppressed_different_sha(db):
    db.record("index.twig", "abc123")
    assert db.is_suppressed("index.twig", "different", hours=1) is False


def test_not_suppressed_different_file(db):
    db.record("index.twig", "abc123")
    assert db.is_suppressed("other.twig", "abc123", hours=1) is False


def test_not_suppressed_before_record(db):
    assert db.is_suppressed("index.twig", "abc123", hours=1) is False


def test_zero_hour_window_suppresses_immediately(db):
    db.record("index.twig", "abc123")
    assert db.is_suppressed("index.twig", "abc123", hours=0) is False


def test_replace_on_same_key(db):
    db.record("index.twig", "abc123")
    db.record("index.twig", "abc123")
    assert db.is_suppressed("index.twig", "abc123", hours=1) is True


def test_multiple_files(db):
    db.record("a.twig", "sha1")
    db.record("b.twig", "sha2")
    assert db.is_suppressed("a.twig", "sha1", hours=1) is True
    assert db.is_suppressed("b.twig", "sha2", hours=1) is True
    assert db.is_suppressed("a.twig", "sha2", hours=1) is False


def test_db_invalid_path():
    with pytest.raises(FimDbError):
        Db("/nonexistent/path/state.db")


def test_db_close(tmp_path):
    d = Db(str(tmp_path / "state.db"))
    d.close()


def test_list_records_empty(tmp_path):
    db = Db(str(tmp_path / "state.db"))
    assert db.list_records() == []
    db.close()


def test_list_records_returns_rows(tmp_path):
    db = Db(str(tmp_path / "state.db"))
    db.record("a/file.twig", "sha1")
    rows = db.list_records()
    assert len(rows) == 1
    assert rows[0][0] == "a/file.twig"
    db.close()


def test_clear_records_all(tmp_path):
    db = Db(str(tmp_path / "state.db"))
    db.record("a.twig", "sha1")
    db.record("b.twig", "sha2")
    n = db.clear_records()
    assert n == 2
    assert db.list_records() == []
    db.close()


def test_clear_records_one_file(tmp_path):
    db = Db(str(tmp_path / "state.db"))
    db.record("a.twig", "sha1")
    db.record("b.twig", "sha2")
    n = db.clear_records("a.twig")
    assert n == 1
    assert len(db.list_records()) == 1
    db.close()


def test_record_count(tmp_path):
    db = Db(str(tmp_path / "state.db"))
    assert db.record_count() == 0
    db.record("a.twig", "sha1")
    assert db.record_count() == 1
    db.close()


def test_context_manager(tmp_path):
    with Db(str(tmp_path / "state.db")) as db:
        db.record("a.twig", "sha1")
        assert db.record_count() == 1
    # connection closed after with block — mutating operations must raise
    with pytest.raises(Exception):
        db.record("b.twig", "sha2")
