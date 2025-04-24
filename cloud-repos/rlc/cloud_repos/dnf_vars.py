"""
DNF Variable Management for CIQ Cloud Repos

This module sets DNF variables in /etc/dnf/vars required for proper repository
URL construction using system and cloud metadata.

Variables Managed:
- baseurl1: Primary mirror URL
- baseurl2: Global fallback mirror
- region: Cloud region
"""

import logging
from pathlib import Path
from typing import Optional

BACKUP_SUFFIX = ".bak"

logger = logging.getLogger(__name__)


def _write_dnf_var(
    basepath: Path, name: str, value: str, overwrite: Optional[bool] = True
):
    """
    Creates or updates a DNF variable file with a given value.

    - If the file does not exist, it is created with the specified value.
    - If overwrite is True and the file exists and contains a different value, it is backed up
      (appending '.bak') before being overwritten.
    - If overwrite is False and the file exists, it is not modified.
    - If the file already contains the desired value, no action is taken.

    Args:
        name (str): Name of the DNF variable (e.g., 'region', 'baseurl1').
        value (str): Value to set for the DNF variable.

    Side Effects:
        - Writes to /etc/dnf/vars/
        - Creates .bak files for existing values that are changed
        - Logs all operations
    """
    path = basepath / name

    # Ensure /etc/dnf/vars exists
    basepath.mkdir(parents=True, exist_ok=True)

    # Check if exists and content differs
    if path.exists():
        current_value = path.read_text().strip()
        if current_value == value:
            logger.debug(f"DNF var '{name}' already set correctly.")
            return
        if not overwrite:
            logger.debug(f"DNF var '{name}' already exists and overwrite is False.")
            return
        # Backup
        try:
            backup_path = path.with_suffix(path.suffix + BACKUP_SUFFIX)
            path.rename(backup_path)
            logger.info(f"Backed up existing DNF var '{name}' to '{backup_path.name}'")
        except Exception as e:
            logger.error(f"Cannot backup DNF var '{name}' ({e}), skipping")
            return

    try:
        path.write_text(f"{value}\n")
        logger.info(f"Wrote DNF var '{name}': {value}")
    except Exception as e:
        logger.error(f"Cannot write to DNF var '{name}' ({e}), skipping")


def ensure_all_dnf_vars(
    basepath: Path, primary_url: str, backup_url: str, overwrite: Optional[bool] = True
):
    """
    Sets DNF variables for the primary and backup mirror URLs.

    Args:
        primary_url (str): Preferred mirror.
        backup_url (str): Fallback mirror.
        overwrite (bool): If True, overwrites existing values.
    """
    _write_dnf_var(basepath, "baseurl1", primary_url, overwrite=overwrite)
    _write_dnf_var(basepath, "baseurl2", backup_url, overwrite=overwrite)
