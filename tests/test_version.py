import json
from unittest.mock import patch, MagicMock
from common.version import _fetch_latest, warn_if_update, read_installed_version


def _make_response(tag: str, body: str) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = json.dumps({"tag_name": tag, "body": body}).encode()
    return mock


def test_fetch_latest_returns_none_when_up_to_date(monkeypatch, tmp_path):
    monkeypatch.setattr("common.version.read_installed_version", lambda *a, **kw: "1.2.3")
    resp = _make_response("v1.2.3", 'python_requires: ">=3.9"')
    with patch("urllib.request.urlopen", return_value=resp):
        assert _fetch_latest(str(tmp_path)) is None


def test_fetch_latest_returns_tuple_when_newer(monkeypatch, tmp_path):
    monkeypatch.setattr("common.version.read_installed_version", lambda *a, **kw: "1.0.0")
    resp = _make_response("v1.2.3", 'python_requires: ">=3.9"')
    with patch("urllib.request.urlopen", return_value=resp):
        result = _fetch_latest(str(tmp_path))
    assert result == ("1.0.0", "1.2.3")


def test_fetch_latest_returns_none_when_incompatible_python(monkeypatch, tmp_path):
    monkeypatch.setattr("common.version.read_installed_version", lambda *a, **kw: "1.0.0")
    resp = _make_response("v2.0.0", 'python_requires: ">=99.0"')
    with patch("urllib.request.urlopen", return_value=resp):
        assert _fetch_latest(str(tmp_path)) is None


def test_fetch_latest_silent_on_network_error(tmp_path):
    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        assert _fetch_latest(str(tmp_path)) is None


def test_warn_if_update_prints_upgrade_command(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("common.version.read_installed_version", lambda *a, **kw: "1.0.0")
    resp = _make_response("v1.2.3", 'python_requires: ">=3.9"')
    with patch("urllib.request.urlopen", return_value=resp):
        warn_if_update(str(tmp_path))
    out = capsys.readouterr().out
    assert "eccube-fim upgrade" in out
    assert "1.2.3" in out


def test_read_installed_version_reads_stamp_file(tmp_path):
    (tmp_path / ".version").write_text("1.2.3\n")
    assert read_installed_version(str(tmp_path)) == "1.2.3"


def test_read_installed_version_strips_whitespace(tmp_path):
    (tmp_path / ".version").write_text("  1.2.3  \n")
    assert read_installed_version(str(tmp_path)) == "1.2.3"


def test_read_installed_version_returns_dev_when_missing(tmp_path):
    assert read_installed_version(str(tmp_path)) == "dev"
