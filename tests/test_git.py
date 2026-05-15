import subprocess
import pytest
from fim.git import git_status, git_diff, file_mtime
from fim.exceptions import FimGitError


def _commit_file(repo, filename, content):
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", filename], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True)


def test_git_status_clean_repo(repo):
    assert git_status(str(repo)) == {}


def test_git_status_modified(repo):
    _commit_file(repo, "index.twig", "original")
    (repo / "index.twig").write_text("tampered")
    status = git_status(str(repo))
    assert "index.twig" in status
    assert "M" in status["index.twig"]


def test_git_status_untracked(repo):
    (repo / "untracked.twig").write_text("new file")
    status = git_status(str(repo))
    assert "untracked.twig" in status
    assert "?" in status["untracked.twig"]


def test_git_status_deleted(repo):
    _commit_file(repo, "index.twig", "original")
    (repo / "index.twig").unlink()
    status = git_status(str(repo))
    assert "index.twig" in status
    assert "D" in status["index.twig"]


def test_git_diff_returns_diff(repo):
    _commit_file(repo, "index.twig", "original\n")
    (repo / "index.twig").write_text("tampered\n")
    diff = git_diff(str(repo), "index.twig")
    assert "-original" in diff
    assert "+tampered" in diff


def test_git_diff_max_lines(repo):
    _commit_file(repo, "big.twig", "")
    lines = "\n".join(f"line{i}" for i in range(200))
    (repo / "big.twig").write_text(lines)
    diff = git_diff(str(repo), "big.twig", max_lines=10)
    assert "more lines omitted" in diff
    assert len(diff.splitlines()) == 11


def test_git_status_invalid_path(tmp_path):
    with pytest.raises(FimGitError):
        git_status(str(tmp_path))


def test_file_mtime_existing(repo):
    (repo / "index.twig").write_text("x")
    mtime = file_mtime(str(repo), "index.twig")
    assert "JST" in mtime


def test_file_mtime_missing(repo):
    result = file_mtime(str(repo), "nonexistent.twig")
    assert result == "(file not found)"
