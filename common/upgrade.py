import json
import os
import re
import shutil
import sys
import tarfile
import urllib.request

from common.version import REPO_SLUG, VERSION_CHECK_URL

_FETCH_TIMEOUT = 5


def fetch_release_info() -> tuple[str, str]:
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
        raise RuntimeError("No releases found — publish a GitHub release first")
    m = re.search(r'python_requires:\s*"(.*?)"', data.get("body", ""))
    return tag, m.group(1) if m else ""


def check_python_requires(requires: str) -> None:
    """Raise SystemExit(1) if the running Python doesn't meet the requirement."""
    if not requires:
        return
    min_parts = tuple(int(x) for x in requires.lstrip(">=").split("."))
    if sys.version_info[:len(min_parts)] < min_parts:
        running = f"{sys.version_info.major}.{sys.version_info.minor}"
        needed = ".".join(str(x) for x in min_parts)
        print(f"Error: this release requires Python {needed}+ (you have {running}).",
              file=sys.stderr)
        print("You are already on the latest version compatible with your Python.",
              file=sys.stderr)
        raise SystemExit(1)


def download_tarball(version: str, dest_dir: str) -> None:
    """Download and extract the release tarball for `version` into `dest_dir`."""
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
