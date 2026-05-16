import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request

from fim.config import INSTALL_SBIN_DIR, INSTALL_LIB_DIR
from fim.lifecycle import _require_root
from fim.version import REPO_SLUG, VERSION_CHECK_URL


def _fetch_release_info() -> tuple[str, str]:
    """Return (tag, python_requires) from the latest GitHub release.

    Raises RuntimeError if the API is unreachable or no release exists.
    """
    req = urllib.request.Request(VERSION_CHECK_URL,
                                 headers={"User-Agent": "eccube-fim"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
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


def upgrade(yes: bool = False) -> int:
    """Download the latest release and replace library + CLI binary.

    Return 0 on success, 1 on network/API error. Raises SystemExit(1)
    if the release requires a newer Python than the running interpreter.
    """
    if not _require_root():
        return 1
    try:
        version, python_requires = _fetch_release_info()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    _check_python_requires(python_requires)
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
