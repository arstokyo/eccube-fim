import os
import shutil
import subprocess
import sys

from fim.config import (
    DEFAULT_CONFIG_DIR,
    INSTALL_SBIN_DIR, INSTALL_LIB_DIR, INSTALL_SYSTEMD_DIR,
    INSTALL_LOGROTATE_PATH, INSTALL_TMPFILES_PATH,
    INSTALL_TIMER_NAME, INSTALL_SERVICE_NAME,
)


def _require_root() -> bool:
    """Return True if running as root; print an error and return False otherwise."""
    if os.geteuid() == 0:
        return True
    print("Error: must be run as root", file=sys.stderr)
    return False


def _systemctl(*args: str) -> None:
    # non-zero is normal when unit is already stopped/disabled
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
