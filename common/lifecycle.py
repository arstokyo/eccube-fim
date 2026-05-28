import os
import shutil
import subprocess
import sys
from pathlib import Path


def require_root() -> bool:
    """Return True if running as root; print an error and return False otherwise."""
    if os.geteuid() == 0:
        return True
    print("Error: must be run as root", file=sys.stderr)
    return False


def stop_and_disable_units(units: list[str]) -> None:
    """Stop and disable each systemd unit; non-zero exit is normal (already stopped)."""
    for unit in units:
        subprocess.run(["systemctl", "stop",    unit], check=False)
        subprocess.run(["systemctl", "disable", unit], check=False)


def remove_unit_files(names: list[str], systemd_dir: str) -> None:
    """Unlink unit files from systemd_dir then reload the daemon."""
    for name in names:
        Path(systemd_dir, name).unlink(missing_ok=True)
    subprocess.run(["systemctl", "daemon-reload"], check=False)


def remove_lib_subdir(lib_dir: str, subdir: str) -> None:
    """Remove lib_dir/subdir only; sibling subdirs and lib_dir itself are untouched."""
    shutil.rmtree(Path(lib_dir) / subdir, ignore_errors=True)


def remove_common_if_no_companion(lib_dir: str, companion_marker: str) -> None:
    """Remove common/ and lib_dir (if empty) only when companion_marker is absent.

    companion_marker is the on-disk file whose presence means the companion tool
    is still installed and still needs common/.
    """
    if Path(companion_marker).exists():
        print("common/ retained — companion tool is still installed.")
        return
    shutil.rmtree(Path(lib_dir) / "common", ignore_errors=True)
    lib = Path(lib_dir)
    if lib.is_dir() and not any(lib.iterdir()):
        lib.rmdir()
