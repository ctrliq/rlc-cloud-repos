#!/usr/bin/env python3

import sys
from typing import Any, Dict, List, Optional

import yaml

try:
    import configargparse
except ImportError:  # pragma: no cover
    print("Error: configargparse is required. Install with: pip -e install framework")
    sys.exit(1)


def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """Load YAML file and return parsed data.

    Args:
        file_path: Path to the YAML file to load

    Returns:
        Parsed YAML data as dictionary
    """
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def extract_active_regions(metadata: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract active (non-commented) regions from Azure metadata.

    Args:
        metadata: Parsed Azure metadata YAML

    Returns:
        List of active regions with their names and pairs
    """
    active_regions = []
    for region in metadata.get("Regions", []):
        # Skip commented out regions (they won't be in the list)
        if region and "name" in region:
            active_regions.append(
                {
                    "name": region["name"],
                    "regional_pair": region.get("regional_pair", ""),
                }
            )
    return active_regions


def generate_mirror_urls(regions: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """Generate mirror URLs for each active region.

    Args:
        regions: List of regions with their names and pairs

    Returns:
        Dictionary of region names mapped to primary and backup URLs
    """
    mirrors = {}
    for region in regions:
        name = region["name"]
        pair = region["regional_pair"]

        mirrors[name] = {
            "primary": f"https://depot.{name}.prod.azure.ciq.com",
            "backup": f"https://depot.{pair}.prod.azure.ciq.com",
        }
    return mirrors


def preserve_default_entry(existing_mirrors: Dict[str, Any]) -> Dict[str, str]:
    """Extract the default entry from existing mirrors.

    Args:
        existing_mirrors: Existing mirrors configuration

    Returns:
        Default mirror configuration
    """
    return existing_mirrors["azure"]["default"]


def transform_azure_mirrors(
    metadata_path: str, mirrors_path: str, output_path: Optional[str] = None
) -> Dict[str, Any]:
    """Transform Azure metadata to mirror format.

    Args:
        metadata_path: Path to the Azure metadata YAML file
        mirrors_path: Path to the existing mirrors YAML file
        output_path: Optional path to write the transformed YAML

    Returns:
        Updated mirrors configuration
    """
    # Load YAML files
    azure_metadata = load_yaml_file(metadata_path)
    ciq_mirrors = load_yaml_file(mirrors_path)

    # Extract active regions and their pairs
    active_regions = extract_active_regions(azure_metadata)

    # Generate mirror URLs
    azure_mirrors = generate_mirror_urls(active_regions)

    # Preserve default entry
    azure_mirrors["default"] = preserve_default_entry(ciq_mirrors)

    # Create the new azure section
    new_ciq_mirrors = ciq_mirrors.copy()
    new_ciq_mirrors["azure"] = azure_mirrors

    # Write to output file if specified
    if output_path:
        with open(output_path, "w") as f:
            yaml.dump(new_ciq_mirrors, f, default_flow_style=False)

    return new_ciq_mirrors


def parse_args(args=None):
    """Parse command line arguments with configargparse.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Parsed arguments
    """
    parser = configargparse.ArgumentParser(
        description="Transform Azure metadata to mirror format.",
        default_config_files=[
            "~/.config/rlc-azure-mirrors.conf",
            "/etc/rlc-azure-mirrors.conf",
        ],
        config_file_parser_class=configargparse.YAMLConfigFileParser,
    )

    parser.add_argument(
        "-c",
        "--config",
        is_config_file=True,
        help="Config file path (can also use ~/.config/rlc-azure-mirrors.conf or /etc/rlc-azure-mirrors.conf)",
    )

    parser.add_argument(
        "--metadata",
        env_var="AZURE_METADATA_PATH",
        default="azure.metadata.yaml",
        help="Path to the Azure metadata YAML file (default: azure.metadata.yaml)",
    )

    parser.add_argument(
        "--mirrors",
        env_var="CIQ_MIRRORS_PATH",
        default="src/rlc_cloud_repos/data/ciq-mirrors.yaml",
        help="Path to the existing mirrors YAML file (default: src/rlc_cloud_repos/data/ciq-mirrors.yaml)",
    )

    parser.add_argument(
        "--output",
        env_var="OUTPUT_PATH",
        help="Path to write the transformed YAML (default: stdout)",
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        env_var="VERIFY_ONLY",
        help="Verify only, report if changes would be made (no output)",
    )

    return parser.parse_args(args)


def main(args=None):
    """Main entry point for the script.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        parsed_args = parse_args(args)

        # Transform the Azure mirrors
        new_mirrors = transform_azure_mirrors(
            parsed_args.metadata,
            parsed_args.mirrors,
            parsed_args.output if not parsed_args.verify else None,
        )

        # If verify mode, check if there are changes
        if parsed_args.verify:
            existing_mirrors = load_yaml_file(parsed_args.mirrors)
            if new_mirrors["azure"] != existing_mirrors["azure"]:
                print("Changes detected in Azure mirrors configuration.")
                return 1
            else:
                print("No changes detected in Azure mirrors configuration.")
                return 0

        # If no output file specified, print to stdout
        if not parsed_args.output:
            print(yaml.dump(new_mirrors, default_flow_style=False))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
