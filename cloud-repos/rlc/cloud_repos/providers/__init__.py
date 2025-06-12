from pathlib import Path
from typing import Optional

from ..dnf_vars import write_dnf_var
from .aws import configure_aws


def configure_default(
    basepath: Path,
    primary_url: str,
    backup_url: str,
    overwrite: Optional[bool] = True,
):
    """
    Sets DNF variables for the primary and backup mirror URLs. Does not modify existing values for product, variant, or
    cloudcontentdir

    Args:
        primary_url (str): Preferred mirror. backup_url (str): Fallback mirror. overwrite (bool): If True, overwrites
        existing values.
    """
    write_dnf_var(basepath, "baseurl1", primary_url, overwrite)
    write_dnf_var(basepath, "baseurl2", backup_url, overwrite)


def configure_provider(
    basepath: Path,
    provider: str,
    primary_url: str,
    backup_url: str,
    overwrite: Optional[bool] = True,
):
    """
    Sets DNF variables for the provider-specific primary and backup mirror URLs.
    Args:
        provider (str): Cloud provider name (e.g., "aws", "azure").
        primary_url (str): Preferred mirror for the provider.
        backup_url (str): Fallback mirror for the provider.
    """
    configure_default(basepath, primary_url, backup_url, overwrite)

    if provider == "aws":

        configure_aws(basepath, primary_url, backup_url, overwrite)
