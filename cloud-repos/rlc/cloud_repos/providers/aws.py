from pathlib import Path
from typing import Optional

from ..dnf_vars import write_dnf_var


def configure_aws(
    basepath: Path, primary_url: str, backup_url: str, overwrite: Optional[bool] = True
):
    """
    Sets DNF variables for the AWS provider environment. Deletes existing values for product, variant, or
    cloudcontentdir as those are not set in the AWS Depot mirrors. Also sets up primary urls in regions without
    contents.

    There are three states: no bucket, bucket with only a region-config file, and a bucket with contents.

    In the case of the no bucket situation, we set the primary URL to a a default mirror.

    Args:
        primary_url (str): Preferred mirror. backup_url (str): Fallback mirror. overwrite (bool): If True, overwrites
        existing values.
    """
    write_dnf_var(basepath, "product", "", overwrite)
    write_dnf_var(basepath, "variant", "", overwrite)
    write_dnf_var(basepath, "cloudcontentdir", "", overwrite)
