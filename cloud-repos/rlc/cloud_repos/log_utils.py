# src/rlc_cloud_repos/log_utils.py
"""
Logging utility for cloud-init-friendly stdout/stderr output.
"""

import logging
import sys

logger = logging.getLogger("rlc-cloud-repos")


def setup_logging(debug: bool = False) -> None:
    """
    Configure logging to emit INFO and lower messages to stdout,
    and warnings and errors to stderr.

    This aligns with cloud-init expectations (no syslog).
    """
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Avoid adding duplicate handlers
    if logger.hasHandlers():
        return

    # Handler for INFO and lower messages to stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    stdout_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(stdout_handler)

    # Handler for warnings and errors to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(stderr_handler)
