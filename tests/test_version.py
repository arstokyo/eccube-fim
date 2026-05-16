import json
from unittest.mock import patch, MagicMock
from fim.version import _fetch_latest, warn_if_update


def _make_response(tag: str, body: str) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = json.dumps({"tag_name": tag, "body": body}).encode()
    return mock


def test_fetch_latest_returns_none_when_up_to_date(monkeypatch):
    import fim.version as v
    monkeypatch.setattr(v, "__version__", "1.2.3")
    resp = _make_response("v1.2.3", 'python_requires: ">=3.9"')
    with patch("urllib.request.urlopen", return_value=resp):
        assert v._fetch_latest() is None


def test_fetch_latest_returns_tuple_when_newer(monkeypatch):
    import fim.version as v
    monkeypatch.setattr(v, "__version__", "1.0.0")
    resp = _make_response("v1.2.3", 'python_requires: ">=3.9"')
    with patch("urllib.request.urlopen", return_value=resp):
        result = v._fetch_latest()
    assert result == ("1.0.0", "1.2.3")


def test_fetch_latest_returns_none_when_incompatible_python(monkeypatch):
    import fim.version as v
    monkeypatch.setattr(v, "__version__", "1.0.0")
    resp = _make_response("v2.0.0", 'python_requires: ">=99.0"')
    with patch("urllib.request.urlopen", return_value=resp):
        assert v._fetch_latest() is None


def test_fetch_latest_silent_on_network_error():
    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        assert _fetch_latest() is None


def test_warn_if_update_prints_upgrade_command(monkeypatch, capsys):
    import fim.version as v
    monkeypatch.setattr(v, "__version__", "1.0.0")
    resp = _make_response("v1.2.3", 'python_requires: ">=3.9"')
    with patch("urllib.request.urlopen", return_value=resp):
        warn_if_update()
    out = capsys.readouterr().out
    assert "eccube-fim upgrade" in out
    assert "1.2.3" in out
