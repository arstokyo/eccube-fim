import os
import pytest
from unittest.mock import patch

from fim.editor import edit_config_file, open_in_editor, show_config


@pytest.fixture
def config_dir(tmp_path):
    (tmp_path / "daemon.yaml").write_text(
        "root_path: /tmp/repo\nstate_db: /tmp/state.db\n", encoding="utf-8"
    )
    (tmp_path / "targets.yaml").write_text(
        "target_files:\n  - app/template/default/Shopping/index.twig\n",
        encoding="utf-8",
    )
    (tmp_path / "notify.yaml").write_text(
        "email:\n  smtp_host: smtp.example.com\n  from: a@b.com\n  recipients: [a@b.com]\n",
        encoding="utf-8",
    )
    return str(tmp_path)


def test_edit_config_file_invalid_which(config_dir, capsys):
    rc = edit_config_file(config_dir, "unknown")
    assert rc == 1
    assert "Unknown config file" in capsys.readouterr().err


def test_edit_config_file_no_change_skips_validation(config_dir, capsys):
    with patch("fim.editor.open_in_editor") as mock_editor:
        with patch("fim.editor.validate_config") as mock_validate:
            rc = edit_config_file(config_dir, "targets")
    mock_editor.assert_called_once()
    mock_validate.assert_not_called()
    assert rc == 0
    assert "No changes made" in capsys.readouterr().out


def test_edit_config_file_validates_when_file_changes(config_dir):
    def _modify(path):
        with open(path, "a", encoding="utf-8") as f:
            f.write("  # comment\n")
        return True  # match open_in_editor's bool contract

    with patch("fim.editor.open_in_editor", side_effect=_modify):
        with patch("fim.editor.load_config") as mock_load:
            with patch("fim.editor.validate_config", return_value=True) as mock_validate:
                rc = edit_config_file(config_dir, "targets")
    mock_load.assert_called_once()
    mock_validate.assert_called_once()
    assert rc == 0


def test_edit_config_file_reports_validation_error(config_dir):
    def _corrupt_file(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("deduplication:\n  suppress_window_hours: 1\n")
        return True  # match open_in_editor's bool contract

    with patch("fim.editor.open_in_editor", side_effect=_corrupt_file):
        rc = edit_config_file(config_dir, "targets")
    assert rc == 1


def test_edit_config_file_missing_file(capsys, tmp_path):
    empty_dir = str(tmp_path / "empty")
    os.makedirs(empty_dir)
    rc = edit_config_file(empty_dir, "daemon")
    assert rc == 1
    assert "Not found" in capsys.readouterr().err


def test_open_in_editor_uses_EDITOR_env(tmp_path):
    test_file = str(tmp_path / "f.txt")
    with patch.dict(os.environ, {"EDITOR": "myeditor"}):
        with patch("fim.editor.subprocess.run") as mock_run:
            open_in_editor(test_file)
    mock_run.assert_called_once_with(["myeditor", test_file])


def test_open_in_editor_falls_back_to_vi(tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in ("EDITOR", "VISUAL")}
    with patch.dict(os.environ, env, clear=True):
        with patch("fim.editor.subprocess.run") as mock_run:
            open_in_editor(str(tmp_path / "f.txt"))
    mock_run.assert_called_once_with(["vi", str(tmp_path / "f.txt")])


def test_open_in_editor_uses_VISUAL_fallback(tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in ("EDITOR", "VISUAL")}
    env["VISUAL"] = "nano"
    with patch.dict(os.environ, env, clear=True):
        with patch("fim.editor.subprocess.run") as mock_run:
            open_in_editor(str(tmp_path / "f.txt"))
    mock_run.assert_called_once_with(["nano", str(tmp_path / "f.txt")])


def test_show_config_prints_sections(config_dir, capsys):
    from fim.config import load_config
    cfg = load_config(config_dir)
    show_config(cfg, config_dir)
    out = capsys.readouterr().out
    assert "[daemon.yaml]" in out
    assert "[targets.yaml]" in out
    assert "[notify.yaml]" in out
    assert "smtp.example.com" in out


def test_show_config_lists_target_files(config_dir, capsys):
    from fim.config import load_config
    cfg = load_config(config_dir)
    show_config(cfg, config_dir)
    out = capsys.readouterr().out
    assert "Shopping/index.twig" in out


def test_show_config_slack_disabled(config_dir, capsys):
    from fim.config import load_config
    cfg = load_config(config_dir)
    show_config(cfg, config_dir)
    out = capsys.readouterr().out
    assert "slack  : disabled" in out
