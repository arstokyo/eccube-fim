import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from malware.clamav_version import (
    get_installed_version,
    get_available_version,
    get_available_version_cached,
    is_update_available,
    invalidate_cache,
)


# ---------------------------------------------------------------------------
# get_installed_version
# ---------------------------------------------------------------------------

def test_get_installed_version_parses_output():
    mock_result = MagicMock(returncode=0, stdout="ClamAV 1.2.3/27004/Mon May 26 2026\n")
    with patch("subprocess.run", return_value=mock_result):
        assert get_installed_version() == "1.2.3"


def test_get_installed_version_not_found():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert get_installed_version() is None


def test_get_installed_version_timeout():
    import subprocess
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="clamscan", timeout=5)):
        assert get_installed_version() is None


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def test_cache_roundtrip(tmp_path, monkeypatch):
    cache = str(tmp_path / "cache")
    monkeypatch.setattr("malware.clamav_version._CACHE_FILE", cache)
    from malware import clamav_version as cv
    cv._write_cache("1.3.0")
    assert cv._read_cache() == "1.3.0"


def test_cache_expired(tmp_path, monkeypatch):
    cache = str(tmp_path / "cache")
    monkeypatch.setattr("malware.clamav_version._CACHE_FILE", cache)
    monkeypatch.setattr("malware.clamav_version._CACHE_TTL", 1)
    from malware import clamav_version as cv
    cv._write_cache("1.3.0")
    # Manually backdate the cache
    old_ts = int(time.time()) - 2
    Path(cache).write_text(f"1.3.0:{old_ts}")
    assert cv._read_cache() is None


def test_cache_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("malware.clamav_version._CACHE_FILE", str(tmp_path / "no-cache"))
    from malware import clamav_version as cv
    assert cv._read_cache() is None


# ---------------------------------------------------------------------------
# _query_dnf / _query_apt
# ---------------------------------------------------------------------------

def test_query_dnf_parses_version():
    dnf_output = (
        "Available Packages\n"
        "Name         : clamav\n"
        "Version      : 1.4.1\n"
        "Release      : 1.el9\n"
    )
    mock_result = MagicMock(returncode=0, stdout=dnf_output)
    with patch("subprocess.run", return_value=mock_result):
        from malware.clamav_version import _query_dnf
        assert _query_dnf() == "1.4.1"


def test_query_apt_parses_candidate():
    apt_output = (
        "clamav:\n"
        "  Installed: 1.2.1\n"
        "  Candidate: 1.2.3+dfsg-1ubuntu1\n"
    )
    mock_result = MagicMock(returncode=0, stdout=apt_output)
    with patch("subprocess.run", return_value=mock_result):
        from malware.clamav_version import _query_apt
        assert _query_apt() == "1.2.3"


# ---------------------------------------------------------------------------
# get_available_version_cached — never calls pkg manager
# ---------------------------------------------------------------------------

def test_get_available_version_cached_cold(tmp_path, monkeypatch):
    monkeypatch.setattr("malware.clamav_version._CACHE_FILE", str(tmp_path / "no-cache"))
    assert get_available_version_cached() is None


def test_get_available_version_cached_warm(tmp_path, monkeypatch):
    cache = str(tmp_path / "cache")
    monkeypatch.setattr("malware.clamav_version._CACHE_FILE", cache)
    from malware import clamav_version as cv
    cv._write_cache("1.4.0")
    assert get_available_version_cached() == "1.4.0"


# ---------------------------------------------------------------------------
# is_update_available
# ---------------------------------------------------------------------------

def test_is_update_available_returns_tuple_when_different(tmp_path, monkeypatch):
    monkeypatch.setattr("malware.clamav_version._CACHE_FILE", str(tmp_path / "cache"))
    from malware import clamav_version as cv
    cv._write_cache("1.4.0")
    mock_installed = MagicMock(returncode=0, stdout="ClamAV 1.2.1/27000\n")
    with patch("subprocess.run", return_value=mock_installed):
        result = is_update_available()
    assert result == ("1.2.1", "1.4.0")


def test_is_update_available_returns_none_when_same(tmp_path, monkeypatch):
    monkeypatch.setattr("malware.clamav_version._CACHE_FILE", str(tmp_path / "cache"))
    from malware import clamav_version as cv
    cv._write_cache("1.2.1")
    mock_installed = MagicMock(returncode=0, stdout="ClamAV 1.2.1/27000\n")
    with patch("subprocess.run", return_value=mock_installed):
        result = is_update_available()
    assert result is None


# ---------------------------------------------------------------------------
# invalidate_cache
# ---------------------------------------------------------------------------

def test_invalidate_cache_removes_file(tmp_path, monkeypatch):
    cache = str(tmp_path / "cache")
    monkeypatch.setattr("malware.clamav_version._CACHE_FILE", cache)
    from malware import clamav_version as cv
    cv._write_cache("1.4.0")
    assert Path(cache).exists()
    invalidate_cache()
    assert not Path(cache).exists()


def test_invalidate_cache_noop_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("malware.clamav_version._CACHE_FILE", str(tmp_path / "no-cache"))
    invalidate_cache()  # should not raise
