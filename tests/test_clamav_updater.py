from unittest.mock import patch, MagicMock

import pytest

from malware.clamav_updater import upgrade_clamav, _detect_pkg_manager, _do_upgrade


# ---------------------------------------------------------------------------
# _detect_pkg_manager
# ---------------------------------------------------------------------------

def test_detect_pkg_manager_dnf():
    with patch("shutil.which", side_effect=lambda x: "/usr/bin/dnf" if x == "dnf" else None):
        assert _detect_pkg_manager() == "dnf"


def test_detect_pkg_manager_apt():
    with patch("shutil.which", side_effect=lambda x: "/usr/bin/apt-get" if x == "apt-get" else None):
        assert _detect_pkg_manager() == "apt"


def test_detect_pkg_manager_none():
    with patch("shutil.which", return_value=None):
        assert _detect_pkg_manager() is None


# ---------------------------------------------------------------------------
# _do_upgrade
# ---------------------------------------------------------------------------

def test_do_upgrade_dnf_calls_correct_command():
    mock_result = MagicMock(returncode=0)
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        rc = _do_upgrade("dnf")
    mock_run.assert_called_once_with(
        ["dnf", "update", "-y", "clamav"], check=False
    )
    assert rc == 0


def test_do_upgrade_apt_calls_correct_command():
    mock_result = MagicMock(returncode=0)
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        rc = _do_upgrade("apt")
    mock_run.assert_called_once_with(
        ["apt-get", "install", "-y", "--only-upgrade", "clamav"], check=False
    )
    assert rc == 0


# ---------------------------------------------------------------------------
# upgrade_clamav
# ---------------------------------------------------------------------------

def test_upgrade_clamav_no_pkg_manager(capsys):
    with patch("malware.clamav_updater._detect_pkg_manager", return_value=None):
        rc = upgrade_clamav(yes=True)
    assert rc == 1
    assert "no supported package manager" in capsys.readouterr().err


def test_upgrade_clamav_already_up_to_date(capsys):
    with patch("malware.clamav_updater._detect_pkg_manager", return_value="dnf"), \
         patch("malware.clamav_updater.get_installed_version", return_value="1.2.3"), \
         patch("malware.clamav_updater.get_available_version", return_value="1.2.3"):
        rc = upgrade_clamav(yes=True)
    assert rc == 0
    assert "already up to date" in capsys.readouterr().out


def test_upgrade_clamav_success(capsys):
    with patch("malware.clamav_updater._detect_pkg_manager", return_value="dnf"), \
         patch("malware.clamav_updater.get_installed_version", side_effect=["1.2.1", "1.2.3"]), \
         patch("malware.clamav_updater.get_available_version", return_value="1.2.3"), \
         patch("malware.clamav_updater._do_upgrade", return_value=0), \
         patch("malware.clamav_updater.invalidate_cache"):
        rc = upgrade_clamav(yes=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "1.2.1" in out
    assert "1.2.3" in out


def test_upgrade_clamav_failure(capsys):
    with patch("malware.clamav_updater._detect_pkg_manager", return_value="dnf"), \
         patch("malware.clamav_updater.get_installed_version", return_value="1.2.1"), \
         patch("malware.clamav_updater.get_available_version", return_value="1.2.3"), \
         patch("malware.clamav_updater._do_upgrade", return_value=1):
        rc = upgrade_clamav(yes=True)
    assert rc == 1
    assert "Upgrade failed" in capsys.readouterr().err


def test_upgrade_clamav_abort_on_no_confirm(capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    with patch("malware.clamav_updater._detect_pkg_manager", return_value="dnf"), \
         patch("malware.clamav_updater.get_installed_version", return_value="1.2.1"), \
         patch("malware.clamav_updater.get_available_version", return_value="1.2.3"):
        rc = upgrade_clamav(yes=False)
    assert rc == 0
    assert "Aborted" in capsys.readouterr().out
