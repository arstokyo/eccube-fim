import pytest
from pathlib import Path
from unittest.mock import patch

from fim.template_ops import (
    list_templates, show_template, edit_template,
    reset_template, preview_template,
)


@pytest.fixture
def config_dir(tmp_path):
    return str(tmp_path)


def test_list_templates_shows_all_names(config_dir, capsys):
    rc = list_templates(config_dir)
    out = capsys.readouterr().out
    assert rc == 0
    assert "email" in out
    assert "slack" in out
    assert "subject" in out
    assert "built-in" in out


def test_show_builtin_template(config_dir, capsys):
    rc = show_template(config_dir, "subject")
    out = capsys.readouterr().out
    assert rc == 0
    assert "built-in" in out
    assert "[ALERT]" in out


def test_show_unknown_template(config_dir, capsys):
    rc = show_template(config_dir, "nonexistent")
    assert rc == 1
    assert "Unknown template" in capsys.readouterr().err


def test_edit_copies_builtin_on_first_use(config_dir):
    with patch("fim.template_ops.open_in_editor"):
        edit_template(config_dir, "email")
    override = Path(config_dir) / "templates" / "email_body.txt"
    assert override.exists()


def test_edit_does_not_overwrite_existing_override(config_dir):
    override_dir = Path(config_dir) / "templates"
    override_dir.mkdir()
    override_file = override_dir / "email_body.txt"
    override_file.write_text("CUSTOM CONTENT", encoding="utf-8")
    with patch("fim.template_ops.open_in_editor"):
        edit_template(config_dir, "email")
    assert override_file.read_text(encoding="utf-8") == "CUSTOM CONTENT"


def test_reset_removes_override(config_dir):
    override_dir = Path(config_dir) / "templates"
    override_dir.mkdir()
    override_file = override_dir / "email_body.txt"
    override_file.write_text("CUSTOM", encoding="utf-8")
    rc = reset_template(config_dir, "email")
    assert rc == 0
    assert not override_file.exists()


def test_reset_no_override_is_noop(config_dir, capsys):
    rc = reset_template(config_dir, "email")
    assert rc == 0
    assert "already using built-in" in capsys.readouterr().out


def test_list_shows_override_when_present(config_dir, capsys):
    override_dir = Path(config_dir) / "templates"
    override_dir.mkdir()
    (override_dir / "email_body.txt").write_text("CUSTOM", encoding="utf-8")
    list_templates(config_dir)
    assert "override" in capsys.readouterr().out


def test_list_override_path_reflects_config_dir(config_dir, capsys):
    override_dir = Path(config_dir) / "templates"
    override_dir.mkdir()
    (override_dir / "email_body.txt").write_text("CUSTOM", encoding="utf-8")
    list_templates(config_dir)
    out = capsys.readouterr().out
    assert config_dir in out


def test_edit_warns_on_missing_template_variable(config_dir, capsys):
    override_dir = Path(config_dir) / "templates"
    override_dir.mkdir()
    bad_template = override_dir / "email_body.txt"
    bad_template.write_text("original", encoding="utf-8")

    def _write_bad(path):
        Path(path).write_text(
            "Hello $hostname on $detected_at\n$file_blocks\n", encoding="utf-8"
        )
        return True  # match open_in_editor's bool contract

    with patch("fim.template_ops.open_in_editor", side_effect=_write_bad):
        edit_template(config_dir, "email")
    assert "Warning" in capsys.readouterr().err


def test_edit_no_warning_when_variables_intact(config_dir, capsys):
    override_dir = Path(config_dir) / "templates"
    override_dir.mkdir()
    initial = override_dir / "email_body.txt"
    initial.write_text("original", encoding="utf-8")

    def _write_good(path):
        Path(path).write_text(
            "Host: $hostname at $detected_at\nCount: $file_count\n$file_blocks\n",
            encoding="utf-8",
        )
        return True  # match open_in_editor's bool contract

    with patch("fim.template_ops.open_in_editor", side_effect=_write_good):
        edit_template(config_dir, "email")
    assert "Warning" not in capsys.readouterr().err


def test_edit_prints_saved_when_file_changes(config_dir, capsys):
    def _modify(path):
        Path(path).write_text(
            "Host: $hostname at $detected_at\nCount: $file_count\n$file_blocks\n",
            encoding="utf-8",
        )
        return True  # match open_in_editor's bool contract
    with patch("fim.template_ops.open_in_editor", side_effect=_modify):
        rc = edit_template(config_dir, "email")
    assert rc == 0
    assert "Template saved" in capsys.readouterr().out


def test_edit_prints_no_changes_when_file_unchanged(config_dir, capsys):
    with patch("fim.template_ops.open_in_editor"):   # no-op editor
        rc = edit_template(config_dir, "email")
    assert rc == 0
    assert "No changes made" in capsys.readouterr().out


def test_preview_renders_all_sections(config_dir, capsys):
    rc = preview_template(config_dir)
    out = capsys.readouterr().out
    assert rc == 0
    assert "SUBJECT" in out
    assert "EMAIL BODY" in out
    assert "SLACK BODY" in out
    assert "Shopping/index.twig" in out


def test_reset_unknown_template(config_dir, capsys):
    rc = reset_template(config_dir, "nonexistent")
    assert rc == 1
    assert "Unknown template" in capsys.readouterr().err


def test_edit_unknown_template(config_dir, capsys):
    rc = edit_template(config_dir, "nonexistent")
    assert rc == 1
    assert "Unknown template" in capsys.readouterr().err
