import subprocess
import pytest
from fim.check import run_detection, run
from fim.config import Config, NotifyEmail, NotifySlack


def _commit_file(repo, filename, content):
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", filename], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True)


def test_clean_repo_no_detections(cfg, db):
    assert run_detection(cfg, db) == []


def test_modified_target_detected(cfg, db, repo):
    _commit_file(repo, "index.twig", "original\n")
    (repo / "index.twig").write_text("tampered <script src='/evil.js'></script>\n")
    results = run_detection(cfg, db)
    assert len(results) == 1
    assert results[0].path == "index.twig"
    assert results[0].full_path.endswith("index.twig")
    assert results[0].root_path == str(repo)


def test_non_target_file_ignored(cfg, db, repo):
    _commit_file(repo, "index.twig", "original\n")
    _commit_file(repo, "other.twig", "other\n")
    (repo / "other.twig").write_text("tampered\n")
    results = run_detection(cfg, db)
    assert results == []


def test_suppression_within_window(cfg, db, repo):
    _commit_file(repo, "index.twig", "original\n")
    (repo / "index.twig").write_text("tampered\n")
    first = run_detection(cfg, db)
    assert len(first) == 1
    # simulate what run() does after dispatch — record so next call suppresses
    for d in first:
        db.record(d.path, d.sha256)
    results = run_detection(cfg, db)
    assert results == []


def test_different_diff_not_suppressed(cfg, db, repo):
    _commit_file(repo, "index.twig", "original\n")
    (repo / "index.twig").write_text("tampered v1\n")
    first = run_detection(cfg, db)
    for d in first:
        db.record(d.path, d.sha256)
    (repo / "index.twig").write_text("tampered v2 — different change\n")
    second = run_detection(cfg, db)
    assert len(second) == 1


def test_deleted_file_detected(cfg, db, repo):
    _commit_file(repo, "index.twig", "original\n")
    (repo / "index.twig").unlink()
    results = run_detection(cfg, db)
    assert len(results) == 1
    assert results[0].diff == "(file deleted)"


def test_run_dry_run_no_record(cfg, tmp_path, repo):
    cfg.state_db = str(tmp_path / "state.db")
    cfg.heartbeat_enabled = False
    _commit_file(repo, "index.twig", "original\n")
    (repo / "index.twig").write_text("tampered\n")
    # dry-run should not record to DB — second run should still detect
    run(cfg, dry_run=True)
    from fim.db import Db
    db2 = Db(cfg.state_db)
    assert run_detection(cfg, db2) != []
    db2.close()


def test_run_returns_0_on_clean(cfg, tmp_path):
    cfg.state_db = str(tmp_path / "state.db")
    cfg.heartbeat_enabled = False
    result = run(cfg, dry_run=True)
    assert result == 0
