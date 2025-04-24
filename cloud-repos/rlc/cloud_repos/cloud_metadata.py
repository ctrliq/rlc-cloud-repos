# src/rlc_cloud_repos/cloud_metadata.py
"""
RLC Cloud Repos - Cloud Metadata Detection

Extracts normalized cloud provider and region from cloud-init query.
"""

import logging
import subprocess
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def get_cloud_metadata(cloudcmd: Optional[str] = None) -> Dict[str, str]:
    """
    Detects the cloud environment using cloud-init's query tool.

    Returns:
        dict[str, str]: Dictionary with keys 'provider' and 'region'

    Raises:
        RuntimeError: If cloud-init query fails.
    """
    if cloudcmd is None:
        cloudcmd = "cloud-init"
    try:
        # we use universal_newlines=True to get the output as a string. the text attribute was added in 3.7+.
        provider = subprocess.check_output(
            [cloudcmd, "query", "cloud_name"], universal_newlines=True
        ).strip()
        region = subprocess.check_output(
            [cloudcmd, "query", "region"], universal_newlines=True
        ).strip()
        return {"provider": provider, "region": region}
    except FileNotFoundError as e:
        logger.error("cloud-init command not found: %s", e)
        raise RuntimeError("The cloud-init command was not found")
    except subprocess.CalledProcessError as e:
        logger.error("Failed to query cloud-init: %s", e)
        raise RuntimeError(
            f"cloud-init must be available and functional: An error occurred while querying cloud-init {e}"
        )
