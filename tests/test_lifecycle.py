import os
import shutil
import sys
import tarfile
import pytest
from fim.lifecycle import uninstall
from fim.upgrade import upgrade


@pytest.fixture
def fake_install(monkeypatch, tmp_path):
    """Redirect all lifecycle install paths to tmp_path."""
    monkeypatch.setattr("fim.lifecycle.INSTALL_SBIN_DIR",       str(tmp_path))
    monkeypatch.setattr("fim.lifecycle.INSTALL_LIB_DIR",        str(tmp_path / "lib"))
    monkeypatch.setattr("fim.lifecycle.INSTALL_SYSTEMD_DIR",    str(tmp_path / "systemd"))
    monkeypatch.setattr("fim.lifecycle.INSTALL_LOGROTATE_PATH", str(tmp_path / "logrotate"))
    monkeypatch.setattr("fim.lifecycle.INSTALL_TMPFILES_PATH",  str(tmp_path / "tmpfiles"))
    monkeypatch.setattr("fim.lifecycle.DEFAULT_CONFIG_DIR",     str(tmp_path / "cfg"))
    monkeypatch.setattr("fim.lifecycle._systemctl", lambda *a: None)
    monkeypatch.setattr("os.geteuid", lambda: 0)

    (tmp_path / "eccube-fim").write_text("")
    (tmp_path / "lib").mkdir()
    (tmp_path / "cfg").mkdir()
    (tmp_path / "systemd").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------

def test_uninstall_fails_when_not_root(monkeypatch, capsys):
    monkeypatch.setattr("os.geteuid", lambda: 1000)
    assert uninstall(yes=True) == 1
    assert "root" in capsys.readouterr().err


def test_uninstall_cancels_on_no(monkeypatch, capsys):
    monkeypatch.setattr("os.geteuid", lambda: 0)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert uninstall(yes=False) == 1
    assert "Cancelled" in capsys.readouterr().out


def test_uninstall_removes_files(fake_install):
    tmp = fake_install
    assert uninstall(keep_config=False, yes=True) == 0
    assert not (tmp / "lib").exists()
    assert not (tmp / "cfg").exists()


def test_uninstall_preserves_config_with_keep_config(fake_install):
    tmp = fake_install
    assert uninstall(keep_config=True, yes=True) == 0
    assert not (tmp / "lib").exists()
    assert (tmp / "cfg").exists()


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def test_upgrade_fails_when_not_root(monkeypatch, capsys):
    monkeypatch.setattr("os.geteuid", lambda: 1000)
    assert upgrade(yes=True) == 1
    assert "root" in capsys.readouterr().err


def test_upgrade_errors_on_api_failure(monkeypatch, capsys):
    monkeypatch.setattr("os.geteuid", lambda: 0)

    def _fail():
        raise RuntimeError("Could not reach GitHub releases API: timeout")

    monkeypatch.setattr("fim.upgrade._fetch_release_info", _fail)
    assert upgrade(yes=True) == 1
    assert "Error" in capsys.readouterr().err


def test_upgrade_errors_on_incompatible_python(monkeypatch, capsys):
    monkeypatch.setattr("os.geteuid", lambda: 0)
    monkeypatch.setattr("fim.upgrade._fetch_release_info",
                        lambda: ("v2.0.0", ">=99.0"))
    with pytest.raises(SystemExit) as exc:
        upgrade(yes=True)
    assert exc.value.code == 1
    assert "Python 99.0+" in capsys.readouterr().err


def test_upgrade_cancels_on_no(monkeypatch, capsys):
    monkeypatch.setattr("os.geteuid", lambda: 0)
    monkeypatch.setattr("fim.upgrade._fetch_release_info",
                        lambda: ("v1.2.3", ">=3.9"))
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert upgrade(yes=False) == 1
    assert "Cancelled" in capsys.readouterr().out


def test_upgrade_replaces_files(monkeypatch, tmp_path):
    fake_src = tmp_path / "src"
    (fake_src / "fim").mkdir(parents=True)
    (fake_src / "fim" / "cli.py").write_text("# updated")
    (fake_src / "fim" / "version.py").write_text('__version__ = "dev"\n')
    (fake_src / "bin").mkdir()
    (fake_src / "bin" / "eccube-fim").write_text("#!/usr/bin/env python3\n")

    archive = tmp_path / "release.tar.gz"
    with tarfile.open(str(archive), "w:gz") as tf:
        tf.add(str(fake_src), arcname="eccube-fim-v1.2.3")

    def fake_download(version: str, dest_dir: str) -> None:
        shutil.copy(str(archive), os.path.join(dest_dir, "eccube-fim.tar.gz"))
        with tarfile.open(os.path.join(dest_dir, "eccube-fim.tar.gz"), "r:gz") as tf:
            if sys.version_info >= (3, 12):
                tf.extractall(dest_dir, filter="data")
            else:
                tf.extractall(dest_dir)
        os.remove(os.path.join(dest_dir, "eccube-fim.tar.gz"))

    lib_dir = tmp_path / "lib"
    (lib_dir / "fim").mkdir(parents=True)
    sbin_dir = tmp_path / "sbin"
    sbin_dir.mkdir()

    monkeypatch.setattr("os.geteuid", lambda: 0)
    monkeypatch.setattr("fim.upgrade._fetch_release_info",
                        lambda: ("v1.2.3", ">=3.9"))
    monkeypatch.setattr("fim.upgrade._download_tarball", fake_download)
    monkeypatch.setattr("fim.upgrade.INSTALL_LIB_DIR",  str(lib_dir))
    monkeypatch.setattr("fim.upgrade.INSTALL_SBIN_DIR", str(sbin_dir))

    assert upgrade(yes=True) == 0
    assert (lib_dir / "fim" / "cli.py").read_text() == "# updated"
    assert (sbin_dir / "eccube-fim").exists()
    assert '__version__ = "1.2.3"' in (lib_dir / "fim" / "version.py").read_text()
