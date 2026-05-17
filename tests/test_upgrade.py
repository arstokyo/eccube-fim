import json
import pytest
from contextlib import ExitStack
from unittest.mock import patch, MagicMock
from fim.upgrade import (
    _check_python_requires,
    _fetch_release_info,
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

def test_upgrade_skips_when_already_at_latest(monkeypatch, capsys):
    import fim.version
    monkeypatch.setattr(fim.version, "__version__", "1.0.0")
    # fim.upgrade binds __version__ at import time; patch both names to keep them in sync
    monkeypatch.setattr("fim.upgrade.__version__", "1.0.0")
    monkeypatch.setattr("os.geteuid", lambda: 0)
    with patch("fim.upgrade._fetch_release_info", return_value=("v1.0.0", "")):
        result = upgrade(yes=True)
    assert result == 0
    out = capsys.readouterr().out
    assert "Already at the latest version" in out
    assert "nothing to do" in out


def test_upgrade_skips_suggests_force(monkeypatch, capsys):
    monkeypatch.setattr("fim.upgrade.__version__", "1.0.0")
    monkeypatch.setattr("os.geteuid", lambda: 0)
    with patch("fim.upgrade._fetch_release_info", return_value=("v1.0.0", "")):
        upgrade(yes=True)
    assert "--force" in capsys.readouterr().out


_INSTALL_PATCHES = [
    "fim.upgrade._download_tarball",
    "fim.upgrade._find_extracted_root",
    "fim.upgrade._stamp_version",
    "shutil.rmtree",
    "shutil.copytree",
    "shutil.copy2",
    "os.chmod",
]


def _patch_install(stack: ExitStack, tmp_path: str) -> None:
    for target in _INSTALL_PATCHES:
        kw = {"return_value": tmp_path} if target == "fim.upgrade._find_extracted_root" else {}
        stack.enter_context(patch(target, **kw))


def test_upgrade_proceeds_when_force_and_same_version(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("fim.upgrade.__version__", "1.0.0")
    monkeypatch.setattr("os.geteuid", lambda: 0)
    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(tmp_path))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path))
    with ExitStack() as stack:
        stack.enter_context(patch("fim.upgrade._fetch_release_info", return_value=("v1.0.0", "")))
        _patch_install(stack, str(tmp_path))
        result = upgrade(yes=True, force=True)
    assert result == 0
    assert "Already at the latest" not in capsys.readouterr().out


def test_upgrade_proceeds_when_newer_version_available(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("fim.upgrade.__version__", "1.0.0")
    monkeypatch.setattr("os.geteuid", lambda: 0)
    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR", str(tmp_path))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(tmp_path))
    with ExitStack() as stack:
        stack.enter_context(patch("fim.upgrade._fetch_release_info", return_value=("v1.1.0", "")))
        _patch_install(stack, str(tmp_path))
        result = upgrade(yes=True)
    assert result == 0
    assert "Already at the latest" not in capsys.readouterr().out
