import os
import shutil

from common.constants import INSTALL_MALWARE_MARKER
from common.lifecycle import (
    require_root as _require_root,
    stop_and_disable_units,
    remove_unit_files,
    remove_lib_subdir,
    remove_common_if_no_companion,
)
from fim.config import (
    DEFAULT_CONFIG_DIR,
    INSTALL_SBIN_DIR, INSTALL_LIB_DIR, INSTALL_SYSTEMD_DIR,
    INSTALL_LOGROTATE_PATH, INSTALL_TMPFILES_PATH,
    INSTALL_TIMER_NAME, INSTALL_SERVICE_NAME,
)

_TIMERS   = [INSTALL_TIMER_NAME]
_SERVICES = [INSTALL_SERVICE_NAME]


def _stop_and_remove_units() -> None:
    stop_and_disable_units(_TIMERS)
    remove_unit_files(_TIMERS + _SERVICES, INSTALL_SYSTEMD_DIR)


def _remove_files(keep_config: bool) -> None:
    for path in (INSTALL_LOGROTATE_PATH, INSTALL_TMPFILES_PATH,
                 os.path.join(INSTALL_SBIN_DIR, "eccube-fim")):
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed {path}")
    remove_lib_subdir(INSTALL_LIB_DIR, "fim")
    remove_common_if_no_companion(INSTALL_LIB_DIR, INSTALL_MALWARE_MARKER)
    if not keep_config and os.path.isdir(DEFAULT_CONFIG_DIR):
        shutil.rmtree(DEFAULT_CONFIG_DIR)
        print(f"Removed {DEFAULT_CONFIG_DIR}")


def uninstall(keep_config: bool = False, yes: bool = False) -> int:
    """Stop the service and remove all installed files. Return 0 on success."""
    if not _require_root():
        return 1
    config_note = " (config preserved)" if keep_config else f" + {DEFAULT_CONFIG_DIR}"
    print(f"This will remove: {INSTALL_SBIN_DIR}/eccube-fim, {INSTALL_LIB_DIR}/fim/{config_note}")
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
