# src/rlc_cloud_repos/repo_config.py
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

from rlc.cloud_repos.log_utils import logger


def load_mirror_map(yaml_path: str) -> Dict[str, Any]:
    """
    Loads the YAML mirror map config.

    Args:
        yaml_path (str): Path to YAML config.

    Returns:
        Dict[str, Any]: Mirror map dictionary.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If YAML is invalid.
    """
    path = Path(yaml_path)

    if not path.exists():
        logger.error(f"Mirror YAML not found at {yaml_path}")
        raise FileNotFoundError(f"Mirror config YAML not found at {yaml_path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error("YAML parsing error")
        raise ValueError(f"Invalid YAML in mirror map: {e}")


def select_mirror(
    metadata: Dict[str, str], mirror_map: Dict[str, Any]
) -> Tuple[str, str]:
    """
    Chooses the best primary and backup mirror URLs for the given cloud metadata.

    Returns:
        tuple[str, str]: (primary_url, backup_url)
    """
    provider = metadata["provider"].lower()
    region = metadata["region"]

    # Set up our fallback fallbacks We do not use default values here because we want this to fail in tests if we have a
    # bad file. We must always have a default with primary and backup values set.
    try:
        default_primary = mirror_map["default"]["primary"]
        default_backup = mirror_map["default"]["backup"]
    except KeyError as e:
        logger.error(f"Missing default mirror values: {e}")
        raise ValueError(
            "Mirror map must have a default entry with primary and backup values set."
        )

    logger.info(f"Selecting mirror for provider={provider}, region={region}")

    if provider in mirror_map:
        # The provider was located in the mirror map
        provider_map = mirror_map[provider]
        if region in provider_map:
            # the region was located in the provider map
            region_map = provider_map.get(region, {})
        else:
            # the region was not located in the provider map, use the default for the provider
            region_map = provider_map.get("default", {})
        return region_map.get("primary", default_primary), region_map.get(
            "backup", default_backup
        )

    else:
        logger.info(f"Provider {provider} not found, using default values")
        return default_primary, default_backup
