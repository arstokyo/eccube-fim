import logging
import sys

from fim.utils import LOG_DIR


def setup_logging(verbose: bool = False) -> None:
    """Configure the root 'fim' logger once at process startup."""
    logger = logging.getLogger("fim")
    # guard against double-init when called more than once in the same process
    if logger.handlers:
        return
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    try:
        # fallback for old service files without LogsDirectory; runs as root so mkdir is safe
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(LOG_DIR / "check.log")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError as e:
        logger.warning("Cannot write to log file %s/check.log: %s", LOG_DIR, e)
