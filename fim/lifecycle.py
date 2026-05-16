import json
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

from fim.config import (
    DEFAULT_CONFIG_DIR,
    INSTALL_SBIN_DIR, INSTALL_LIB_DIR, INSTALL_SYSTEMD_DIR,
    INSTALL_LOGROTATE_PATH, INSTALL_TMPFILES_PATH,
    INSTALL_TIMER_NAME, INSTALL_SERVICE_NAME,
)
from fim.version import REPO_SLUG, VERSION_CHECK_URL

log = logging.getLogger(__name__)


def _require_root() -> bool:
    """Return True if running as root; print an error and return False otherwise."""
    if os.geteuid() == 0:
        return True
    print("Error: must be run as root", file=sys.stderr)
    return False


def _systemctl(*args: str) -> None:
    subprocess.run(["systemctl", *args], check=False)


def _stop_and_remove_units() -> None:
    _systemctl("stop", INSTALL_TIMER_NAME, INSTALL_SERVICE_NAME)
    _systemctl("disable", INSTALL_TIMER_NAME)
    for fname in (INSTALL_TIMER_NAME, INSTALL_SERVICE_NAME):
        path = os.path.join(INSTALL_SYSTEMD_DIR, fname)
        if os.path.exists(path):
            os.remove(path)
    _systemctl("daemon-reload")


def _remove_files(keep_config: bool) -> None:
    for path in (INSTALL_LOGROTATE_PATH, INSTALL_TMPFILES_PATH,
                 os.path.join(INSTALL_SBIN_DIR, "eccube-fim")):
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed {path}")
    if os.path.isdir(INSTALL_LIB_DIR):
        shutil.rmtree(INSTALL_LIB_DIR)
        print(f"Removed {INSTALL_LIB_DIR}")
    if not keep_config and os.path.isdir(DEFAULT_CONFIG_DIR):
        shutil.rmtree(DEFAULT_CONFIG_DIR)
        print(f"Removed {DEFAULT_CONFIG_DIR}")


def uninstall(keep_config: bool = False, yes: bool = False) -> int:
    """Stop the service and remove all installed files. Return 0 on success."""
    if not _require_root():
        return 1
    config_note = " (config preserved)" if keep_config else f" + {DEFAULT_CONFIG_DIR}"
    print(f"This will remove: {INSTALL_SBIN_DIR}/eccube-fim, {INSTALL_LIB_DIR}{config_note}")
    if not yes:
        answer = input("Proceed with uninstall? [y/N]: ").strip().lower()
        if answer != "y":
            print("Cancelled")
            return 1
    print("Stopping and disabling systemd units...")
    _stop_and_remove_units()
    _remove_files(keep_config)
    print("Uninstall complete")
    return 0


def _resolve_latest_tag() -> str:
    """Return the latest release tag, or 'main' if no releases exist.

    Falls back to 'main' on network error; logs a warning so the operator
    knows the resolved version before confirming.
    """
    try:
        req = urllib.request.Request(VERSION_CHECK_URL,
                                     headers={"User-Agent": "eccube-fim"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            tag = data.get("tag_name")
            if tag:
                return tag
    except Exception as e:
        log.warning("Could not resolve latest release (%s) — falling back to main", e)
    return "main"


def _download_tarball(version: str, dest_dir: str) -> None:
    if version == "main":
        url = f"https://github.com/{REPO_SLUG}/archive/refs/heads/main.tar.gz"
    else:
        url = f"https://github.com/{REPO_SLUG}/archive/refs/tags/{version}.tar.gz"
    archive = os.path.join(dest_dir, "eccube-fim.tar.gz")
    urllib.request.urlretrieve(url, archive)
    with tarfile.open(archive, "r:gz") as tf:
        # filter='data' blocks path-traversal entries; available Python 3.12+
        if sys.version_info >= (3, 12):
            tf.extractall(dest_dir, filter="data")
        else:
            tf.extractall(dest_dir)
    os.remove(archive)


def _find_extracted_root(dest_dir: str) -> str:
    """Return the single top-level directory created by the tarball extraction."""
    entries = [e for e in os.listdir(dest_dir)
               if os.path.isdir(os.path.join(dest_dir, e))]
    if len(entries) != 1:
        raise RuntimeError(f"Unexpected tarball layout in {dest_dir}: {entries}")
    return os.path.join(dest_dir, entries[0])


def upgrade(yes: bool = False) -> int:
    """Download the latest release and replace library + CLI binary. Return 0 on success."""
    if not _require_root():
        return 1
    version = _resolve_latest_tag()
    print(f"Latest version : {version}")
    print(f"Will replace   : {INSTALL_LIB_DIR}/fim  and  {INSTALL_SBIN_DIR}/eccube-fim")
    if not yes:
        answer = input("Proceed with upgrade? [y/N]: ").strip().lower()
        if answer != "y":
            print("Cancelled")
            return 1
    with tempfile.TemporaryDirectory() as tmp:
        print(f"Downloading eccube-fim {version}...")
        _download_tarball(version, tmp)
        src = _find_extracted_root(tmp)
        print("Replacing library...")
        shutil.rmtree(os.path.join(INSTALL_LIB_DIR, "fim"), ignore_errors=True)
        shutil.copytree(os.path.join(src, "fim"),
                        os.path.join(INSTALL_LIB_DIR, "fim"))
        print("Replacing CLI binary...")
        dest_bin = os.path.join(INSTALL_SBIN_DIR, "eccube-fim")
        shutil.copy2(os.path.join(src, "bin", "eccube-fim"), dest_bin)
        os.chmod(dest_bin, 0o755)
    print(f"Upgrade to {version} complete")
    return 0
