import logging
import sys

from fim.utils import LOG_DIR


def setup_logging(verbose: bool = False) -> None:
    """Configure the root 'eccube-fim' logger once at process startup."""
    logger = logging.getLogger("eccube-fim")
    # guard against double-init when called more than once in the same process
    if logger.handlers:
        return
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    if LOG_DIR.exists():
        fh = logging.FileHandler(LOG_DIR / "check.log")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
