# known: 185 lines — cohesive shared-upgrade orchestration (release fetch, tarball
# extraction, module/binary replacement, migrations, co-upgrade confirmation);
# splitting would fragment one release flow across files for no clarity gain
import json
import os
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Callable

from common.constants import FETCH_TIMEOUT as _FETCH_TIMEOUT, INSTALL_LIB_DIR
from common.lifecycle import require_root
from common.version import (
    REPO_SLUG,
    VERSION_CHECK_URL,
    parse_python_requires,
    python_meets,
    read_installed_version,
)


def fetch_release_info() -> tuple[str, str]:
    """Return (tag, python_requires) from the latest GitHub release.

    Raises RuntimeError if the API is unreachable or no release exists.
    """
    req = urllib.request.Request(VERSION_CHECK_URL,
                                 headers={"User-Agent": "eccube-fim"})
    try:
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except Exception as e:  # known: wraps all urllib/json errors into RuntimeError for callers
        raise RuntimeError(
            f"Could not reach GitHub releases API: {e}\n"
            f"Check your network or visit: https://github.com/{REPO_SLUG}/releases"
        ) from e
    tag = data.get("tag_name")
    if not tag:
        raise RuntimeError("No releases found — publish a GitHub release first")
    return tag, parse_python_requires(data.get("body", ""))


def check_python_requires(requires: str) -> None:
    """Raise SystemExit(1) if the running Python doesn't meet the requirement."""
    if python_meets(requires):
        return
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    needed = requires.lstrip(">=")
    print(f"Error: this release requires Python {needed}+ (you have {running}).",
          file=sys.stderr)
    print("You are already on the latest version compatible with your Python.",
          file=sys.stderr)
    raise SystemExit(1)


def download_tarball(version: str, dest_dir: str) -> None:
    """Download and extract the release tarball for `version` into `dest_dir`.

    The archive is removed after extraction.
    """
    url = f"https://github.com/{REPO_SLUG}/archive/refs/tags/{version}.tar.gz"
    archive = os.path.join(dest_dir, "eccube-fim.tar.gz")
    req = urllib.request.Request(url, headers={"User-Agent": "eccube-fim"})
    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp, \
         open(archive, "wb") as f:
        shutil.copyfileobj(resp, f)
    with tarfile.open(archive, "r:gz") as tf:
        # filter='data' blocks path-traversal entries; available Python 3.12+
        if sys.version_info >= (3, 12):
            tf.extractall(dest_dir, filter="data")
        else:
            tf.extractall(dest_dir)
    os.remove(archive)


def find_extracted_root(dest_dir: str) -> str:
    """Return the single top-level directory created by the tarball extraction."""
    entries = [e for e in os.listdir(dest_dir)
               if os.path.isdir(os.path.join(dest_dir, e))]
    if len(entries) != 1:
        raise RuntimeError(f"Unexpected tarball layout in {dest_dir}: {entries}")
    return os.path.join(dest_dir, entries[0])


def replace_module(src: str, lib_dir: str, subdir: str) -> None:
    """Replace lib_dir/subdir with the freshly extracted copy from src/subdir."""
    shutil.rmtree(os.path.join(lib_dir, subdir), ignore_errors=True)
    shutil.copytree(os.path.join(src, subdir), os.path.join(lib_dir, subdir))


def replace_primary(src: str, lib_dir: str, subdir: str) -> None:
    """Replace the running tool's own module plus the shared common/ package."""
    replace_module(src, lib_dir, subdir)
    replace_module(src, lib_dir, "common")


def replace_companion(src: str, lib_dir: str, subdir: str, bin_dst: str) -> None:
    """Replace the companion tool's module and refresh its CLI binary.

    common/ is left untouched — the primary replacement already refreshed it.
    """
    replace_module(src, lib_dir, subdir)
    shutil.copy2(os.path.join(src, "bin", os.path.basename(bin_dst)), bin_dst)
    os.chmod(bin_dst, 0o755)


def write_version_stamp(config_dir: str, version: str) -> None:
    (Path(config_dir) / ".version").write_text(version.lstrip("v") + "\n", encoding="utf-8")


def run_companion_migrations(config_dir: str, db_name: str, lib_subdir: str) -> int:
    """Run the companion tool's migrations after its code was replaced on disk.

    db_name:    companion's state DB filename under config_dir (e.g. "state.db").
    lib_subdir: companion's package dir under INSTALL_LIB_DIR (e.g. "fim").
    """
    # deferred import — picks up the freshly-replaced common/migration on disk
    from common.migration import MigrationRunner
    return MigrationRunner(
        db_path=str(Path(config_dir) / db_name),
        migrations_dir=str(Path(INSTALL_LIB_DIR) / lib_subdir / "migrations"),
        config_dir=config_dir,
    ).run()


def migrate_only(config_dir: str, cli_name: str,
                 run_migrations: Callable[[str], int]) -> int:
    """Run pending migrations and update version stamp. Return 0 on success.

    run_migrations: tool-specific function that applies pending migrations.
    cli_name: used in the retry hint printed on failure.
    """
    print("Running pending migrations...")
    try:
        count = run_migrations(config_dir)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(f"Fix the error above, then retry: {cli_name} upgrade --migrate-only",
              file=sys.stderr)
        return 1
    print(f"Applied {count} migration(s)." if count else "No pending migrations.")
    try:
        version, _ = fetch_release_info()
        write_version_stamp(config_dir, version)
    except RuntimeError:
        # leave stamp unchanged — next upgrade run will find no pending migrations
        pass
    return 0


def run_upgrade(config_dir: str, yes: bool, force: bool, migrate_only_flag: bool,
                install_release: Callable[[str, bool, str], int],
                migrate_only_fn: Callable[[str], int]) -> int:
    """Drive the standard upgrade flow shared by eccube-fim and eccube-malware.

    `install_release(version, yes, config_dir)` and `migrate_only_fn(config_dir)`
    are the tool-specific steps; the root check, release fetch, Python-version gate,
    and already-current short-circuit are identical for both tools.
    """
    if not require_root():
        return 1
    if migrate_only_flag:
        return migrate_only_fn(config_dir)
    try:
        version, python_requires = fetch_release_info()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    check_python_requires(python_requires)
    installed = read_installed_version(config_dir)
    if version.lstrip("v") == installed and not force:
        print(f"Already at the latest version ({installed}) — nothing to do.")
        print("Use --force to reinstall anyway.")
        return 0
    return install_release(version, yes, config_dir)


def confirm_co_upgrade(tool_name: str, companion: str, version: str, yes: bool) -> bool:
    if yes:
        return True
    print("Co-install detected:")
    print(f"  - {tool_name} will be upgraded to {version}")
    print(f"  - {companion} will also be upgraded to {version}")
    print(f"  - shared eccube-common will be upgraded to {version}")
    answer = input(f"Co-upgrade {companion} too? [y/N]: ").strip().lower()
    return answer == "y"
