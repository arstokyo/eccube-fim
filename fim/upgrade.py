# known: 194 lines — sequential upgrade pipeline; _migrate_only and _install_release are tightly coupled to shared helpers
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from fim.config import INSTALL_SBIN_DIR, INSTALL_LIB_DIR, DEFAULT_CONFIG_DIR
from fim.lifecycle import _require_root
from fim.version import REPO_SLUG, VERSION_CHECK_URL, _FETCH_TIMEOUT, read_installed_version


def _fetch_release_info() -> tuple[str, str]:
    """Return (tag, python_requires) from the latest GitHub release.

    Raises RuntimeError if the API is unreachable or no release exists.
    """
    req = urllib.request.Request(VERSION_CHECK_URL,
                                 headers={"User-Agent": "eccube-fim"})
    try:
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        raise RuntimeError(
            f"Could not reach GitHub releases API: {e}\n"
            f"Check your network or visit: https://github.com/{REPO_SLUG}/releases"
        ) from e
    tag = data.get("tag_name")
    if not tag:
        raise RuntimeError(
            "No releases found — publish a GitHub release before running upgrade"
        )
    body = data.get("body", "")
    m = re.search(r'python_requires:\s*"(.*?)"', body)
    python_requires = m.group(1) if m else ""
    return tag, python_requires


def _check_python_requires(requires: str) -> None:
    """Print error and raise SystemExit(1) if running Python doesn't meet the requirement."""
    if not requires:
        return
    min_parts = tuple(int(x) for x in requires.lstrip(">=").split("."))
    if sys.version_info[:len(min_parts)] < min_parts:
        running = f"{sys.version_info.major}.{sys.version_info.minor}"
        needed = ".".join(str(x) for x in min_parts)
        print(
            f"Error: this release requires Python {needed}+ "
            f"(you have Python {running}).",
            file=sys.stderr,
        )
        print(
            "You are already on the latest version compatible with your Python.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _download_tarball(version: str, dest_dir: str) -> None:
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


def _write_version_stamp(config_dir: str, version: str) -> None:
    """Write the installed version string to the stamp file in config_dir."""
    (Path(config_dir) / ".version").write_text(version.lstrip("v") + "\n", encoding="utf-8")


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
    # known: 40 lines — sequential install steps; splitting would require passing version+config_dir as state
    """Prompt for confirmation, download `version`, replace library + binary.

    Return 0 on success, 1 if the user cancels or migrations fail.
    """
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
