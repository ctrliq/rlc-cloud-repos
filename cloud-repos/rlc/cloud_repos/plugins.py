"""
Plugin system for provider-specific customizations.

Executes shell scripts from /etc/rlc-cloud-repos/plugins.d/ to allow
site-specific customization of DNF variables without code changes.
"""

import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

from .dnf_vars import write_dnf_var
from .log_utils import logger

PLUGINS_DIR = "/etc/rlc-cloud-repos/plugins.d"
PLUGIN_TIMEOUT = 30  # seconds

# Protected DNF variables that plugins cannot override
PROTECTED_VARIABLES = {
    "baseurl1",
    "baseurl2",
    "contentdir",
    "product",
    "cloudcontentdir",
}


def is_safe_plugin(plugin_path: Path) -> bool:
    """
    Validate that a plugin file is safe to execute.

    Args:
        plugin_path: Path to the plugin file

    Returns:
        bool: True if plugin passes safety checks
    """
    try:
        # Check file exists and is a regular file
        if not plugin_path.is_file():
            logger.warning(f"Plugin {plugin_path} is not a regular file")
            return False

        # Get file stats
        file_stat = plugin_path.stat()

        # Check ownership (must be owned by root)
        if file_stat.st_uid != 0:
            logger.warning(
                f"Plugin {plugin_path} not owned by root (uid: {file_stat.st_uid})"
            )
            return False

        # Check permissions (must not be world-writable)
        if file_stat.st_mode & stat.S_IWOTH:
            logger.warning(f"Plugin {plugin_path} is world-writable")
            return False

        # Check if executable
        if not os.access(plugin_path, os.X_OK):
            logger.warning(f"Plugin {plugin_path} is not executable")
            return False

        # Basic shebang check
        with open(plugin_path, "rb") as f:
            first_line = f.readline()
            if not first_line.startswith(b"#!"):
                logger.warning(f"Plugin {plugin_path} missing shebang")
                return False

        return True

    except Exception as e:
        logger.warning(f"Error validating plugin {plugin_path}: {e}")
        return False


def discover_plugins() -> List[Path]:
    """
    Discover and validate plugin scripts in the plugins directory.

    Returns:
        List[Path]: List of safe, executable plugin paths sorted by name
    """
    plugins_path = Path(PLUGINS_DIR)

    if not plugins_path.exists():
        logger.debug(f"Plugins directory {PLUGINS_DIR} does not exist")
        return []

    if not plugins_path.is_dir():
        logger.warning(f"Plugins path {PLUGINS_DIR} is not a directory")
        return []

    # Find all .sh files
    plugins = []
    try:
        for plugin_file in plugins_path.glob("*.sh"):
            if is_safe_plugin(plugin_file):
                plugins.append(plugin_file)
                logger.debug(f"Discovered safe plugin: {plugin_file}")
            else:
                logger.warning(f"Skipping unsafe plugin: {plugin_file}")
    except Exception as e:
        logger.warning(f"Error discovering plugins: {e}")

    return sorted(plugins)


def execute_plugin(
    plugin_path: Path, provider: str, region: str, primary_url: str, backup_url: str
) -> Tuple[bool, Dict[str, str]]:
    """
    Execute a plugin script and parse its output.

    Args:
        plugin_path: Path to the plugin script
        provider: Cloud provider name
        region: Cloud region
        primary_url: Primary mirror URL
        backup_url: Backup mirror URL

    Returns:
        Tuple[bool, Dict[str, str]]: (success, variables_dict)
    """
    cmd = [
        str(plugin_path),
        "--provider",
        provider,
        "--region",
        region,
        "--primary-url",
        primary_url,
        "--backup-url",
        backup_url,
    ]

    logger.info(f"Executing plugin: {plugin_path.name}")
    logger.debug(f"Plugin command: {' '.join(cmd)}")

    try:
        # Execute with timeout and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PLUGIN_TIMEOUT,
            cwd=tempfile.gettempdir(),  # Safe working directory
            env={"PATH": "/usr/bin:/bin"},  # Minimal environment
        )

        if result.returncode != 0:
            logger.warning(
                f"Plugin {plugin_path.name} exited with code {result.returncode}"
            )
            if result.stderr:
                logger.warning(f"Plugin stderr: {result.stderr.strip()}")
            return False, {}

        # Parse output as key=value pairs
        variables = {}
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Basic validation of variable names (must start with letter,
                # contain only alphanumeric, underscore, dash)
                is_valid_name = (
                    key
                    and key.replace("_", "").replace("-", "").isalnum()
                    and key[0].isalpha()
                )
                if is_valid_name:
                    # Check if variable is protected
                    if key.lower() in PROTECTED_VARIABLES:
                        logger.warning(
                            f"Plugin {plugin_path.name} attempted to set protected variable: {key}"
                        )
                    else:
                        variables[key] = value
                        logger.debug(f"Plugin {plugin_path.name} set {key}={value}")
                else:
                    logger.warning(
                        f"Plugin {plugin_path.name} produced invalid variable name: {key}"
                    )
            else:
                logger.debug(f"Plugin {plugin_path.name} output ignored: {line}")

        return True, variables

    except subprocess.TimeoutExpired:
        logger.error(f"Plugin {plugin_path.name} timed out after {PLUGIN_TIMEOUT}s")
        return False, {}
    except Exception as e:
        logger.error(f"Error executing plugin {plugin_path.name}: {e}")
        return False, {}


def run_plugins(
    provider: str, region: str, primary_url: str, backup_url: str
) -> Dict[str, str]:
    """
    Discover and execute all plugins, collecting their output variables.

    Args:
        provider: Cloud provider name
        region: Cloud region
        primary_url: Primary mirror URL
        backup_url: Backup mirror URL

    Returns:
        Dict[str, str]: Combined variables from all successful plugins
    """
    plugins = discover_plugins()

    if not plugins:
        logger.debug("No plugins found")
        return {}

    logger.info(f"Found {len(plugins)} plugin(s)")

    combined_variables = {}

    for plugin_path in plugins:
        success, variables = execute_plugin(
            plugin_path, provider, region, primary_url, backup_url
        )

        if success:
            # Later plugins can override earlier ones
            combined_variables.update(variables)
            logger.debug(
                f"Plugin {plugin_path.name} contributed {len(variables)} variable(s)"
            )
        else:
            logger.warning(f"Plugin {plugin_path.name} failed")

    logger.info(f"Plugins contributed {len(combined_variables)} total variable(s)")
    return combined_variables


def configure_plugins(
    basepath: Path,
    provider: str,
    region: str,
    primary_url: str,
    backup_url: str,
    overwrite: bool = True,
):
    """
    Execute plugins to set additional DNF variables based on provider/region.

    Args:
        basepath (Path): DNF vars directory path
        provider (str): Cloud provider name (e.g., "aws", "azure")
        region (str): Cloud region
        primary_url (str): Primary mirror URL
        backup_url (str): Backup mirror URL
        overwrite (bool): Whether to overwrite existing DNF variables
    """
    logger.info("Running plugins for additional DNF variable customizations")
    plugin_variables = run_plugins(provider, region, primary_url, backup_url)

    for var_name, var_value in plugin_variables.items():
        logger.debug(f"Setting plugin variable: {var_name}={var_value}")
        write_dnf_var(basepath, var_name, var_value, overwrite)

    if plugin_variables:
        logger.info(f"Applied {len(plugin_variables)} plugin-provided variables")
    else:
        logger.debug("No plugin variables to apply")
