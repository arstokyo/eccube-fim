import json
import os
import pytest
from contextlib import ExitStack
from unittest.mock import patch, MagicMock
from common.upgrade import (
    check_python_requires as _check_python_requires,
    fetch_release_info as _fetch_release_info,
)
from fim.upgrade import (
    _find_extracted_root,
    upgrade,
)


# ---------------------------------------------------------------------------
# _check_python_requires
# ---------------------------------------------------------------------------

def test_check_python_requires_passes_when_compatible():
    _check_python_requires(">=3.9")  # running Python is at least 3.9


def test_check_python_requires_passes_on_empty():
    _check_python_requires("")  # no constraint — always passes


def test_check_python_requires_exits_when_incompatible(capsys):
    with pytest.raises(SystemExit) as exc:
        _check_python_requires(">=99.0")
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Python 99.0+" in err
    assert "latest version compatible" in err


# ---------------------------------------------------------------------------
# _fetch_release_info
# ---------------------------------------------------------------------------

def _make_response(tag: str, body: str) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = json.dumps({"tag_name": tag, "body": body}).encode()
    return mock


def test_fetch_release_info_returns_tag_and_requires():
    resp = _make_response("v1.2.3", 'some text\n---\npython_requires: ">=3.9"')
    with patch("urllib.request.urlopen", return_value=resp):
        tag, requires = _fetch_release_info()
    assert tag == "v1.2.3"
    assert requires == ">=3.9"


def test_fetch_release_info_returns_empty_requires_when_absent():
    resp = _make_response("v1.2.3", "no metadata here")
    with patch("urllib.request.urlopen", return_value=resp):
        tag, requires = _fetch_release_info()
    assert tag == "v1.2.3"
    assert requires == ""


def test_fetch_release_info_raises_on_network_error():
    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        with pytest.raises(RuntimeError, match="Could not reach GitHub releases API"):
            _fetch_release_info()


def test_fetch_release_info_raises_when_no_tag():
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = json.dumps({"message": "Not Found"}).encode()
    with patch("urllib.request.urlopen", return_value=mock):
        with pytest.raises(RuntimeError, match="No releases found"):
            _fetch_release_info()


# ---------------------------------------------------------------------------
# _find_extracted_root
# ---------------------------------------------------------------------------

def test_find_extracted_root_returns_single_dir(tmp_path):
    (tmp_path / "eccube-fim-v1.2.3").mkdir()
    assert _find_extracted_root(str(tmp_path)).endswith("eccube-fim-v1.2.3")


def test_find_extracted_root_raises_on_multiple_dirs(tmp_path):
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir2").mkdir()
    with pytest.raises(RuntimeError, match="Unexpected tarball layout"):
        _find_extracted_root(str(tmp_path))


def test_find_extracted_root_ignores_files(tmp_path):
    (tmp_path / "eccube-fim-v1.2.3").mkdir()
    (tmp_path / "some_file.txt").write_text("ignored")
    assert _find_extracted_root(str(tmp_path)).endswith("eccube-fim-v1.2.3")


# ---------------------------------------------------------------------------
# upgrade — version equality check
# ---------------------------------------------------------------------------

def test_upgrade_skips_when_already_at_latest(monkeypatch, tmp_path, capsys):
    (tmp_path / ".version").write_text("1.0.0\n")
    monkeypatch.setattr("os.geteuid", lambda: 0)
    with patch("common.upgrade.fetch_release_info", return_value=("v1.0.0", "")):
        result = upgrade(yes=True, config_dir=str(tmp_path))
    assert result == 0
    out = capsys.readouterr().out
    assert "Already at the latest version" in out
    assert "nothing to do" in out


def test_upgrade_skips_suggests_force(monkeypatch, tmp_path, capsys):
    (tmp_path / ".version").write_text("1.0.0\n")
    monkeypatch.setattr("os.geteuid", lambda: 0)
    with patch("common.upgrade.fetch_release_info", return_value=("v1.0.0", "")):
        upgrade(yes=True, config_dir=str(tmp_path))
    assert "--force" in capsys.readouterr().out


_INSTALL_PATCHES = [
    "fim.upgrade._download_tarball",
    "fim.upgrade._find_extracted_root",
    "fim.upgrade._write_version_stamp",
    "fim.upgrade._run_migrations",
    "shutil.rmtree",
    "shutil.copytree",
    "shutil.copy2",
    "os.chmod",
]


def _patch_install(stack: ExitStack, tmp_path: str) -> None:
    for target in _INSTALL_PATCHES:
        if target == "fim.upgrade._find_extracted_root":
            kw = {"return_value": tmp_path}
        elif target == "fim.upgrade._run_migrations":
            kw = {"return_value": 0}
        else:
            kw = {}
        stack.enter_context(patch(target, **kw))


def test_upgrade_proceeds_when_force_and_same_version(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("os.geteuid", lambda: 0)
    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(tmp_path))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path))
    with ExitStack() as stack:
        stack.enter_context(patch("common.upgrade.fetch_release_info", return_value=("v1.0.0", "")))
        _patch_install(stack, str(tmp_path))
        result = upgrade(yes=True, force=True, config_dir=str(tmp_path))
    assert result == 0
    assert "Already at the latest" not in capsys.readouterr().out


def test_upgrade_proceeds_when_newer_version_available(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("os.geteuid", lambda: 0)
    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(tmp_path))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path))
    with ExitStack() as stack:
        stack.enter_context(patch("common.upgrade.fetch_release_info", return_value=("v1.1.0", "")))
        _patch_install(stack, str(tmp_path))
        result = upgrade(yes=True, config_dir=str(tmp_path))
    assert result == 0
    assert "Already at the latest" not in capsys.readouterr().out


def test_upgrade_does_not_write_stamp_when_migration_fails(monkeypatch, tmp_path):
    monkeypatch.setattr("os.geteuid", lambda: 0)
    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(tmp_path))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path))
    with ExitStack() as stack:
        stack.enter_context(patch("common.upgrade.fetch_release_info",
                                  return_value=("v1.1.0", "")))
        stack.enter_context(patch("fim.upgrade._download_tarball"))
        stack.enter_context(patch("fim.upgrade._find_extracted_root",
                                  return_value=str(tmp_path)))
        stack.enter_context(patch("shutil.rmtree"))
        stack.enter_context(patch("shutil.copytree"))
        stack.enter_context(patch("fim.upgrade._run_migrations",
                                  side_effect=RuntimeError("boom")))
        result = upgrade(yes=True, config_dir=str(tmp_path))
    assert result == 1
    assert not (tmp_path / ".version").exists()


def test_write_version_stamp_strips_v_prefix(tmp_path):
    from fim.upgrade import _write_version_stamp
    _write_version_stamp(str(tmp_path), "v1.2.3")
    assert (tmp_path / ".version").read_text() == "1.2.3\n"


def test_write_version_stamp_without_v_prefix(tmp_path):
    from fim.upgrade import _write_version_stamp
    _write_version_stamp(str(tmp_path), "1.2.3")
    assert (tmp_path / ".version").read_text() == "1.2.3\n"


# ---------------------------------------------------------------------------
# upgrade --migrate-only
# ---------------------------------------------------------------------------

def test_migrate_only_calls_run_migrations(tmp_path):
    """--migrate-only skips download and runs only migrations."""
    config_dir = str(tmp_path)
    (tmp_path / ".version").write_text("1.0.0\n", encoding="utf-8")

    with patch("common.upgrade.require_root", return_value=True), \
         patch("fim.upgrade._run_migrations", return_value=2) as mock_mig, \
         patch("common.upgrade.fetch_release_info", return_value=("v1.0.0", "")), \
         patch("common.upgrade.write_version_stamp") as mock_stamp, \
         patch("fim.upgrade._download_tarball") as mock_dl:
        rc = upgrade(migrate_only=True, config_dir=config_dir)

    assert rc == 0
    mock_mig.assert_called_once_with(config_dir)
    mock_stamp.assert_called_once()
    mock_dl.assert_not_called()


def test_migrate_only_returns_1_on_failure(tmp_path, capsys):
    config_dir = str(tmp_path)
    with patch("common.upgrade.require_root", return_value=True), \
         patch("fim.upgrade._run_migrations", side_effect=RuntimeError("bad")):
        rc = upgrade(migrate_only=True, config_dir=config_dir)
    assert rc == 1
    assert "--migrate-only" in capsys.readouterr().err


def test_migrate_only_no_network_leaves_stamp_unchanged(tmp_path):
    """When GitHub is unreachable, stamp is left unchanged (next upgrade finds no migrations)."""
    config_dir = str(tmp_path)
    (tmp_path / ".version").write_text("1.2.3\n", encoding="utf-8")
    with patch("common.upgrade.require_root", return_value=True), \
         patch("fim.upgrade._run_migrations", return_value=0), \
         patch("common.upgrade.fetch_release_info", side_effect=RuntimeError("no net")), \
         patch("fim.upgrade._write_version_stamp") as mock_stamp:
        rc = upgrade(migrate_only=True, config_dir=config_dir)
    assert rc == 0
    mock_stamp.assert_not_called()


# ---------------------------------------------------------------------------
# _install_release copies both fim/ and common/
# ---------------------------------------------------------------------------

def test_install_release_copies_fim_and_common(monkeypatch, tmp_path):
    """Both fim/ and common/ must be copied from the tarball."""
    from fim.upgrade import _install_release

    src = tmp_path / "src"
    (src / "fim").mkdir(parents=True)
    (src / "common").mkdir()
    (src / "bin").mkdir()
    (src / "bin" / "eccube-fim").write_text("#!/bin/sh", encoding="utf-8")

    copied_dirs: list[str] = []

    def fake_copytree(src_path: str, dst_path: str) -> None:
        copied_dirs.append(os.path.basename(src_path))

    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(tmp_path / "lib"))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path / "sbin"))

    with patch("fim.upgrade._download_tarball"), \
         patch("fim.upgrade._find_extracted_root", return_value=str(src)), \
         patch("fim.upgrade._run_migrations", return_value=0), \
         patch("fim.upgrade._write_version_stamp"), \
         patch("shutil.rmtree"), \
         patch("shutil.copytree", side_effect=fake_copytree), \
         patch("shutil.copy2"), \
         patch("os.chmod"):
        rc = _install_release("v1.1.0", yes=True, config_dir=str(tmp_path))

    assert rc == 0
    assert "fim" in copied_dirs, "fim/ must be copied"
    assert "common" in copied_dirs, "common/ must be copied"


def test_install_release_prompt_mentions_common(monkeypatch, tmp_path, capsys):
    """Confirmation prompt must name common/ so the user knows what changes."""
    from fim.upgrade import _install_release

    src = tmp_path / "src"
    (src / "fim").mkdir(parents=True)
    (src / "common").mkdir()
    (src / "bin").mkdir()
    (src / "bin" / "eccube-fim").write_text("#!/bin/sh", encoding="utf-8")

    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(tmp_path / "lib"))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path / "sbin"))

    with patch("fim.upgrade._download_tarball"), \
         patch("fim.upgrade._find_extracted_root", return_value=str(src)), \
         patch("fim.upgrade._run_migrations", return_value=0), \
         patch("fim.upgrade._write_version_stamp"), \
         patch("shutil.rmtree"), \
         patch("shutil.copytree"), \
         patch("shutil.copy2"), \
         patch("os.chmod"):
        _install_release("v1.1.0", yes=True, config_dir=str(tmp_path))

    out = capsys.readouterr().out
    assert "common" in out, "Prompt must mention common/"


# ---------------------------------------------------------------------------
# co-install: fim upgrade also replaces malware/ when co-installed
# ---------------------------------------------------------------------------

def test_install_release_co_install_copies_malware(monkeypatch, tmp_path):
    """When malware/ exists under INSTALL_LIB_DIR, fim upgrade copies it too."""
    from fim.upgrade import _install_release

    src = tmp_path / "src"
    for d in ("fim", "common", "malware", "bin"):
        (src / d).mkdir(parents=True)
    (src / "bin" / "eccube-fim").write_text("#!/bin/sh")
    (src / "bin" / "eccube-malware").write_text("#!/bin/sh")

    lib_dir = tmp_path / "lib"
    (lib_dir / "malware").mkdir(parents=True)  # companion is installed

    copied_dirs: list[str] = []

    def fake_copytree(src_path: str, dst_path: str) -> None:
        copied_dirs.append(os.path.basename(src_path))

    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(lib_dir))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path / "sbin"))
    monkeypatch.setattr("fim.upgrade._MALWARE_BIN", str(tmp_path / "sbin" / "eccube-malware"))

    with patch("fim.upgrade._download_tarball"), \
         patch("fim.upgrade._find_extracted_root", return_value=str(src)), \
         patch("fim.upgrade._run_migrations", return_value=0), \
         patch("fim.upgrade._run_malware_migrations", return_value=0), \
         patch("fim.upgrade._write_version_stamp"), \
         patch("shutil.rmtree"), \
         patch("shutil.copytree", side_effect=fake_copytree), \
         patch("shutil.copy2"), \
         patch("os.chmod"):
        rc = _install_release("v1.1.0", yes=True, config_dir=str(tmp_path))

    assert rc == 0
    assert "malware" in copied_dirs, "malware/ must be copied when co-installed"


def test_install_release_no_co_install_skips_malware(monkeypatch, tmp_path):
    """When malware/ does not exist, fim upgrade must NOT copy malware/."""
    from fim.upgrade import _install_release

    src = tmp_path / "src"
    for d in ("fim", "common", "bin"):
        (src / d).mkdir(parents=True)
    (src / "bin" / "eccube-fim").write_text("#!/bin/sh")

    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()  # no malware/ subdir — companion not installed

    copied_dirs: list[str] = []

    def fake_copytree(src_path: str, dst_path: str) -> None:
        copied_dirs.append(os.path.basename(src_path))

    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(lib_dir))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path / "sbin"))

    with patch("fim.upgrade._download_tarball"), \
         patch("fim.upgrade._find_extracted_root", return_value=str(src)), \
         patch("fim.upgrade._run_migrations", return_value=0), \
         patch("fim.upgrade._write_version_stamp"), \
         patch("shutil.rmtree"), \
         patch("shutil.copytree", side_effect=fake_copytree), \
         patch("shutil.copy2"), \
         patch("os.chmod"):
        rc = _install_release("v1.1.0", yes=True, config_dir=str(tmp_path))

    assert rc == 0
    assert "malware" not in copied_dirs, "malware/ must NOT be copied for single-tool install"


def test_install_release_co_install_prompt_mentions_malware(monkeypatch, tmp_path, capsys):
    """Confirmation prompt mentions malware/ when co-installed."""
    from fim.upgrade import _install_release

    src = tmp_path / "src"
    for d in ("fim", "common", "malware", "bin"):
        (src / d).mkdir(parents=True)
    (src / "bin" / "eccube-fim").write_text("#!/bin/sh")
    (src / "bin" / "eccube-malware").write_text("#!/bin/sh")

    lib_dir = tmp_path / "lib"
    (lib_dir / "malware").mkdir(parents=True)

    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(lib_dir))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path / "sbin"))
    monkeypatch.setattr("fim.upgrade._MALWARE_BIN", str(tmp_path / "sbin" / "eccube-malware"))

    with patch("fim.upgrade._download_tarball"), \
         patch("fim.upgrade._find_extracted_root", return_value=str(src)), \
         patch("fim.upgrade._run_migrations", return_value=0), \
         patch("fim.upgrade._run_malware_migrations", return_value=0), \
         patch("fim.upgrade._write_version_stamp"), \
         patch("shutil.rmtree"), \
         patch("shutil.copytree"), \
         patch("shutil.copy2"), \
         patch("os.chmod"):
        _install_release("v1.1.0", yes=True, config_dir=str(tmp_path))

    out = capsys.readouterr().out
    assert "malware" in out, "Prompt must mention malware/ for co-install"


def test_install_release_single_install_prompt_omits_malware(monkeypatch, tmp_path, capsys):
    """Confirmation prompt does NOT mention malware/ for single-tool install."""
    from fim.upgrade import _install_release

    src = tmp_path / "src"
    for d in ("fim", "common", "bin"):
        (src / d).mkdir(parents=True)
    (src / "bin" / "eccube-fim").write_text("#!/bin/sh")

    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()  # no malware/ subdir

    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(lib_dir))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path / "sbin"))

    with patch("fim.upgrade._download_tarball"), \
         patch("fim.upgrade._find_extracted_root", return_value=str(src)), \
         patch("fim.upgrade._run_migrations", return_value=0), \
         patch("fim.upgrade._write_version_stamp"), \
         patch("shutil.rmtree"), \
         patch("shutil.copytree"), \
         patch("shutil.copy2"), \
         patch("os.chmod"):
        _install_release("v1.1.0", yes=True, config_dir=str(tmp_path))

    out = capsys.readouterr().out
    assert "malware" not in out, "Prompt must NOT mention malware/ for single-tool install"


# ---------------------------------------------------------------------------
# co-upgrade prompt: operator must confirm before companion is replaced
# ---------------------------------------------------------------------------

def test_fim_upgrade_co_install_prompts_before_companion_upgrade(monkeypatch, tmp_path, capsys):
    """When malware is installed and the operator answers 'n', upgrade cancels before download."""
    (tmp_path / ".version").write_text("1.1.0\n")
    monkeypatch.setattr("os.geteuid", lambda: 0)
    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(tmp_path / "lib"))
    (tmp_path / "lib" / "malware").mkdir(parents=True)  # simulate co-install

    with patch("common.upgrade.fetch_release_info", return_value=("v1.2.0", "")), \
         patch("fim.upgrade._download_tarball") as mock_dl, \
         patch("builtins.input", return_value="n"):
        result = upgrade(yes=False, config_dir=str(tmp_path))

    assert result == 1
    mock_dl.assert_not_called()
    out = capsys.readouterr().out
    assert "Co-install detected" in out
    assert "Cancelled" in out


def test_fim_upgrade_yes_allows_co_upgrade_without_prompt(monkeypatch, tmp_path):
    """When --yes is passed for co-install, upgrade proceeds without prompting."""
    (tmp_path / ".version").write_text("1.1.0\n")
    monkeypatch.setattr("os.geteuid", lambda: 0)
    lib_dir = tmp_path / "lib"
    (lib_dir / "malware").mkdir(parents=True)
    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(lib_dir))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path / "sbin"))
    monkeypatch.setattr("fim.upgrade._MALWARE_BIN", str(tmp_path / "sbin" / "eccube-malware"))

    with patch("common.upgrade.fetch_release_info", return_value=("v1.2.0", "")), \
         patch("fim.upgrade._download_tarball"), \
         patch("fim.upgrade._find_extracted_root", return_value=str(tmp_path / "src")), \
         patch("fim.upgrade._replace_fim_libraries"), \
         patch("fim.upgrade._replace_malware_companion"), \
         patch("fim.upgrade._run_migrations", return_value=0), \
         patch("fim.upgrade._run_malware_migrations", return_value=0), \
         patch("fim.upgrade._write_version_stamp"), \
         patch("shutil.copy2"), \
         patch("os.chmod"), \
         patch("builtins.input") as mock_input:
        result = upgrade(yes=True, config_dir=str(tmp_path))

    assert result == 0
    mock_input.assert_not_called()
