from pathlib import Path
from typing import Optional

from ..dnf_vars import write_dnf_var


def configure_aws(
    basepath: Path, primary_url: str, backup_url: str, overwrite: Optional[bool] = True
):
    """
    Sets DNF variables for the AWS provider environment. Deletes existing values for product, or cloudcontentdir as
    those are not set in the AWS Depot mirrors. Also sets up primary urls in regions without contents.

    There are three states: no bucket, bucket with only a region-config file, and a bucket with contents.

    All of these cases are pre-handled in the metadata, so we need not do anything special here.

    Args:
        primary_url (str): Preferred mirror. backup_url (str): Fallback mirror. overwrite (bool): If True, overwrites
        existing values.
    """
    write_dnf_var(basepath, "product", "", overwrite)
    write_dnf_var(basepath, "cloudcontentdir", "", overwrite)
