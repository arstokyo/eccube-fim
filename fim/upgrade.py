import os
import shutil
import sys
import tempfile
from pathlib import Path

from common.constants import INSTALL_MALWARE_BIN as _MALWARE_BIN
from common.upgrade import (
    download_tarball as _download_tarball,
    find_extracted_root as _find_extracted_root,
    write_version_stamp as _write_version_stamp,
    confirm_co_upgrade as _confirm_co_upgrade,
    migrate_only as _migrate_only_impl,
    run_upgrade as _run_upgrade,
)
from fim.config import INSTALL_SBIN_DIR, INSTALL_LIB_DIR, DEFAULT_CONFIG_DIR


def _run_migrations(config_dir: str) -> int:
    # deferred import — loads new fim/migration.py after disk replacement
    import fim.migration as _m
    return _m.run_migrations(config_dir)


def _malware_installed() -> bool:
    return os.path.isdir(os.path.join(INSTALL_LIB_DIR, "malware"))


def _replace_fim_libraries(src: str) -> None:
    shutil.rmtree(os.path.join(INSTALL_LIB_DIR, "fim"), ignore_errors=True)
    shutil.copytree(os.path.join(src, "fim"), os.path.join(INSTALL_LIB_DIR, "fim"))
    shutil.rmtree(os.path.join(INSTALL_LIB_DIR, "common"), ignore_errors=True)
    shutil.copytree(os.path.join(src, "common"), os.path.join(INSTALL_LIB_DIR, "common"))


def _replace_malware_companion(src: str) -> None:
    shutil.rmtree(os.path.join(INSTALL_LIB_DIR, "malware"), ignore_errors=True)
    shutil.copytree(os.path.join(src, "malware"), os.path.join(INSTALL_LIB_DIR, "malware"))
    shutil.copy2(os.path.join(src, "bin", "eccube-malware"), _MALWARE_BIN)
    os.chmod(_MALWARE_BIN, 0o755)


def _run_malware_migrations(config_dir: str) -> int:
    # deferred import — loads new common/migration after disk replacement
    from common.migration import MigrationRunner
    return MigrationRunner(
        db_path=str(Path(config_dir) / "malware_state.db"),  # installation convention for malware's state
        migrations_dir=str(Path(INSTALL_LIB_DIR) / "malware" / "migrations"),
        config_dir=config_dir,
    ).run()


def _migrate_only(config_dir: str) -> int:
    return _migrate_only_impl(config_dir, "eccube-fim", _run_migrations)


def _install_release(version: str, yes: bool, config_dir: str) -> int:
    # known: 49 lines — sequential install flow; splitting would require threading
    # co_install state through multiple helpers with no clarity gain
    """Prompt, download `version`, and replace library + binary. Return 0 ok, 1 on failure."""
    co_install = _malware_installed()
    companion_note = f"  {INSTALL_LIB_DIR}/malware  {_MALWARE_BIN}" if co_install else ""
    print(f"Latest version : {version}")
    print(f"Will replace   : {INSTALL_LIB_DIR}/fim  {INSTALL_LIB_DIR}/common  "
          f"{INSTALL_SBIN_DIR}/eccube-fim{companion_note}")
    if co_install:
        if not _confirm_co_upgrade("eccube-fim", "eccube-malware", version, yes):
            print("Cancelled")
            return 1
    elif not yes:
        answer = input("Proceed with upgrade? [y/N]: ").strip().lower()
        if answer != "y":
            print("Cancelled")
            return 1
    with tempfile.TemporaryDirectory() as tmp:
        print(f"Downloading eccube-fim {version}...")
        _download_tarball(version, tmp)
        src = _find_extracted_root(tmp)
        print("Replacing library...")
        _replace_fim_libraries(src)
        if co_install:
            print("Co-install detected — also replacing malware/...")
            _replace_malware_companion(src)
        print("Running migrations...")
        try:
            count = _run_migrations(config_dir)
            if count:
                print(f"Applied {count} migration(s).")
            if co_install:
                mc = _run_malware_migrations(config_dir)
                if mc:
                    print(f"Applied {mc} malware migration(s).")
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
    """Download latest release and replace library + binary. Raises SystemExit(1) on Python mismatch."""
    return _run_upgrade(config_dir, yes, force, migrate_only,
                        _install_release, _migrate_only)
