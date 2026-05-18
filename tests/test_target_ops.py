import pytest
from pathlib import Path
from unittest.mock import patch

from fim.target_ops import list_targets, add_target, remove_target


@pytest.fixture(autouse=True)
def suppress_git_check():
    """Default is_git_tracked to True in all tests; git-tracking tests override."""
    with patch("fim.target_ops.is_git_tracked", return_value=True):
        yield


@pytest.fixture
def config_dir(tmp_path):
    (tmp_path / "daemon.yaml").write_text(
        "root_path: /tmp/repo\nstate_db: /tmp/state.db\n", encoding="utf-8"
    )
    (tmp_path / "targets.yaml").write_text(
        "# --- Target files ---\ntarget_files:\n"
        "  # Shopping pages\n"
        "  - app/template/default/Shopping/index.twig\n"
        "  - app/template/default/Shopping/confirm.twig\n",
        encoding="utf-8",
    )
    (tmp_path / "notify.yaml").write_text(
        "email:\n  smtp_host: smtp.x.com\n  from: a@b.com\n  recipients: [a@b.com]\n",
        encoding="utf-8",
    )
    return str(tmp_path)


def test_list_prints_files(config_dir, capsys):
    rc = list_targets(config_dir)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Shopping/index.twig" in out
    assert "2 file(s)" in out


def test_add_new_path(config_dir):
    rc = add_target(config_dir, "app/template/default/Block/header.twig")
    assert rc == 0
    text = (Path(config_dir) / "targets.yaml").read_text(encoding="utf-8")
    assert "header.twig" in text


def test_add_preserves_comments(config_dir):
    add_target(config_dir, "app/template/default/Block/header.twig")
    text = (Path(config_dir) / "targets.yaml").read_text(encoding="utf-8")
    assert "# --- Target files ---" in text
    assert "# Shopping pages" in text


def test_add_new_entry_inside_target_files_block(config_dir):
    extra = (
        "# --- Target files ---\ntarget_files:\n"
        "  - app/template/default/Shopping/index.twig\n"
        "other_key:\n  - something\n"
    )
    Path(config_dir, "targets.yaml").write_text(extra, encoding="utf-8")
    add_target(config_dir, "app/template/default/Block/header.twig")
    text = (Path(config_dir) / "targets.yaml").read_text(encoding="utf-8")
    idx_new = text.index("header.twig")
    idx_other = text.index("other_key")
    assert idx_new < idx_other


def test_add_duplicate_is_noop(config_dir, capsys):
    rc = add_target(config_dir, "app/template/default/Shopping/index.twig")
    assert rc == 0
    assert "Already monitored" in capsys.readouterr().out


def test_add_missing_file_returns_1(tmp_path, capsys):
    rc = add_target(str(tmp_path), "some/file.twig")
    assert rc == 1
    assert "Cannot read" in capsys.readouterr().err


def test_remove_existing_path(config_dir):
    rc = remove_target(config_dir, "app/template/default/Shopping/confirm.twig")
    assert rc == 0
    text = (Path(config_dir) / "targets.yaml").read_text(encoding="utf-8")
    assert "confirm.twig" not in text


def test_remove_preserves_other_entries(config_dir):
    remove_target(config_dir, "app/template/default/Shopping/confirm.twig")
    text = (Path(config_dir) / "targets.yaml").read_text(encoding="utf-8")
    assert "index.twig" in text


def test_remove_nonexistent_is_noop(config_dir, capsys):
    rc = remove_target(config_dir, "app/template/default/Nonexistent/index.twig")
    assert rc == 0
    assert "nothing to remove" in capsys.readouterr().out


def test_remove_missing_file_returns_1(tmp_path, capsys):
    rc = remove_target(str(tmp_path), "some/file.twig")
    assert rc == 1
    assert "Cannot read" in capsys.readouterr().err


def test_add_warns_when_not_git_tracked(config_dir, capsys):
    with patch("fim.target_ops.is_git_tracked", return_value=False):
        add_target(config_dir, "app/template/default/Block/header.twig")
    assert "may not be tracked in git" in capsys.readouterr().err


def test_add_no_warning_when_git_tracked(config_dir, capsys):
    with patch("fim.target_ops.is_git_tracked", return_value=True):
        add_target(config_dir, "app/template/default/Block/header.twig")
    assert "not be tracked" not in capsys.readouterr().err


def test_add_warns_when_git_unreachable(config_dir, capsys):
    with patch("fim.target_ops.is_git_tracked", return_value=False):
        add_target(config_dir, "app/template/default/Block/header.twig")
    assert "eccube-fim config validate" in capsys.readouterr().err


def test_add_target_succeeds_without_daemon_yaml(tmp_path, capsys):
    """target add works even when daemon.yaml is absent (no cross-file dep)."""
    targets = tmp_path / "targets.yaml"
    targets.write_text("target_files:\n  - app/existing.twig\n")
    with patch("fim.target_ops.is_git_tracked", return_value=True):
        result = add_target(str(tmp_path), "app/new.twig")
    assert result == 0
    text = targets.read_text()
    assert "app/new.twig" in text
