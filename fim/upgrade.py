import os
import shutil
import sys
import tempfile
from pathlib import Path

from common.upgrade import (  # noqa: F401
    fetch_release_info as _fetch_release_info,
    check_python_requires as _check_python_requires,
    download_tarball as _download_tarball,
    find_extracted_root as _find_extracted_root,
    write_version_stamp as _write_version_stamp,
)
from fim.config import INSTALL_SBIN_DIR, INSTALL_LIB_DIR, DEFAULT_CONFIG_DIR
from fim.lifecycle import _require_root
from fim.version import read_installed_version


def _run_migrations(config_dir: str) -> int:
    # deferred import — in production the lib has just been replaced on disk,
    # so importing here loads the new fim/migration.py rather than a cached pre-upgrade version
    import fim.migration as _m
    return _m.run_migrations(config_dir)


def _migrate_only(config_dir: str) -> int:
    """Run pending migrations and update the version stamp. No download.

    Return 0 on success, 1 if migrations fail. Used for upgrade retries
    when code is already in place but state.db migration was interrupted.
    """
    print("Running pending migrations...")
    try:
        count = _run_migrations(config_dir)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(
            "Fix the error above, then retry: eccube-fim upgrade --migrate-only",
            file=sys.stderr,
        )
        return 1
    if count:
        print(f"Applied {count} migration(s).")
    else:
        print("No pending migrations.")
    try:
        version, _ = _fetch_release_info()
        _write_version_stamp(config_dir, version)
    except RuntimeError:
        # leave stamp unchanged — next upgrade run will find no pending migrations
        # and exit cleanly without re-downloading
        pass
    print("Migration retry complete.")
    return 0


def _install_release(version: str, yes: bool, config_dir: str) -> int:
    """Prompt for confirmation, download `version`, replace library + binary.

    Return 0 on success, 1 if the user cancels or migrations fail.
    """
    # known: sequential install steps; splitting would require passing version+config_dir as state
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
        print("Running migrations...")
        try:
            count = _run_migrations(config_dir)
            if count:
                print(f"Applied {count} migration(s).")
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            print(
                "Code is in place. To retry migrations without re-downloading: "
                "eccube-fim upgrade --migrate-only",
                file=sys.stderr,
            )
            return 1
        _write_version_stamp(config_dir, version)
        print("Replacing CLI binary...")
        dest_bin = os.path.join(INSTALL_SBIN_DIR, "eccube-fim")
        shutil.copy2(os.path.join(src, "bin", "eccube-fim"), dest_bin)
        os.chmod(dest_bin, 0o755)
    print(f"Upgrade to {version} complete")
    return 0


def upgrade(yes: bool = False, force: bool = False, migrate_only: bool = False,
            config_dir: str = DEFAULT_CONFIG_DIR) -> int:
    """Download the latest release and replace library + CLI binary.

    Return 0 on success, 1 on network/API error. Raises SystemExit(1)
    if the release requires a newer Python than the running interpreter.
    """
    if not _require_root():
        return 1
    if migrate_only:
        return _migrate_only(config_dir)
    try:
        version, python_requires = _fetch_release_info()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    _check_python_requires(python_requires)
    installed = read_installed_version(config_dir)
    latest_clean = version.lstrip("v")
    if latest_clean == installed and not force:
        print(f"Already at the latest version ({installed}) — nothing to do.")
        print("Use --force to reinstall anyway.")
        return 0
    return _install_release(version, yes, config_dir)
