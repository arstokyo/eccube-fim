import json
import pytest
from unittest.mock import patch, MagicMock
from fim.upgrade import (
    _check_python_requires,
    _fetch_release_info,
    _find_extracted_root,
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
