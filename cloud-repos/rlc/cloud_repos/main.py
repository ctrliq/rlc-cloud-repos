#!env python
"""
RLC Cloud Repo Resolver CLI

This tool detects the cloud provider and region via cloud-init,
selects the appropriate CIQ repository mirror, and writes DNF vars
for optimized regional repo access.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from rlc.cloud_repos import __version__ as rlc_version
from rlc.cloud_repos.cloud_metadata import get_cloud_metadata
from rlc.cloud_repos.log_utils import logger, setup_logging
from rlc.cloud_repos.providers import configure_provider
from rlc.cloud_repos.repo_config import load_mirror_map, select_mirror

MARKERFILE = "/etc/rlc-cloud-repos/.configured"
DEFAULT_MIRROR_PATH = "/usr/share/rlc-cloud-repos/ciq-mirrors.yaml"
DNF_VARS_DIR = "/etc/dnf/vars"


def check_touchfile() -> bool:
    """
    Check if the system has already been configured.
    Returns True if marker file exists, indicating configuration should be skipped.

    Returns:
        bool: True if marker file exists, False otherwise
    """
    if os.path.exists(MARKERFILE):
        logger.info(f"Marker file exists ({MARKERFILE}). Skipping repo update.")
        return True
    return False


def write_touchfile() -> None:
    """
    Create a touchfile to indicate configuration was completed.
    Prevents automatic reruns on reboot (cloud-init idempotency).
    """
    os.makedirs(os.path.dirname(MARKERFILE), exist_ok=True)
    with open(MARKERFILE, "w") as f:
        f.write(f"Configured on {datetime.now().isoformat()}\n")


def _configure_repos(mirror_file_path: str) -> None:
    """
    Core logic for detecting metadata, selecting mirrors, and configuring DNF vars.
    """
    # Detect provider + region via cloud-init query
    overwrite = True
    try:
        metadata = get_cloud_metadata()
    except Exception as e:
        logger.error(f"Failed to get cloud metadata: {e}")
        metadata = {"provider": "unknown", "region": "unknown"}
        # An error happened. We want to continue to write dnf vars, but we don't want to overwrite if they are already
        # set. This is so that we don't break the "non-cloud" case.
        overwrite = False

    provider = metadata["provider"]
    region = metadata["region"]
    logger.info(f"Using cloud metadata: provider={provider}, region={region}")

    # Load mirror map + resolve appropriate URL
    mirror_map = load_mirror_map(mirror_file_path)
    logger.info(f"Loaded mirror map from {mirror_file_path}")

    primary_url, backup_url = select_mirror(
        {"provider": provider, "region": region}, mirror_map
    )
    logger.info(f"Selected mirror URL: {primary_url}")

    # Set DNF vars
    vars_dir = Path(DNF_VARS_DIR)
    configure_provider(vars_dir, provider, primary_url, backup_url, overwrite)

    # Create marker file to prevent future reruns
    write_touchfile()
    logger.info(f"Marker file written to {MARKERFILE}")


def parse_args(args=None):
    """
    Parse command line arguments

    Args:
        args: Command line arguments (defaults to None, which uses sys.argv[1:])

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="RLC Cloud Repo Resolver version %s" % rlc_version,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--mirror-file", help="Override path to mirror map YAML")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reconfiguration (ignore marker file)",
    )
    return parser.parse_args(args)


def main(args=None) -> int:
    """
    Entry point for RLC cloud repo resolver. Handles argument parsing and
    calls the core configuration logic.

    Args:
        args: Command line arguments (defaults to None, which uses sys.argv[1:])

    Returns:
        int: 0 for success, 1 for failure
    """
    if os.geteuid() != 0:
        logger.error("This program must be run as root.")
        return 1

    setup_logging()

    parsed_args = parse_args(args)

    if not parsed_args.force:
        if check_touchfile():  # Skip configuration if marker file exists
            return 0

    mirror_path = parsed_args.mirror_file or DEFAULT_MIRROR_PATH
    try:
        _configure_repos(mirror_path)
        return 0
    except Exception as e:
        logger.error("Configuration failed: %s", e, exc_info=False)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))  # pragma: no cover.git
