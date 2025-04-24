from pathlib import Path

import pytest
import yaml

from rlc_cloud_repos_framework import azure_mirrors as am

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_load_yaml_file(mirrors_file):
    data = am.load_yaml_file(str(mirrors_file))
    assert isinstance(data, dict)
    assert "azure" in data


def test_extract_active_regions():
    metadata = {
        "Regions": [
            {"name": "eastus", "regional_pair": "westus2"},
            {"name": "westus2", "regional_pair": "eastus"},
            None,  # Test handling of None entries
            {"wrongkey": "should be skipped"},  # Test handling of invalid entries
        ]
    }
    regions = am.extract_active_regions(metadata)
    assert len(regions) == 2
    assert regions[0]["name"] == "eastus"
    assert regions[0]["regional_pair"] == "westus2"
    assert regions[1]["name"] == "westus2"
    assert regions[1]["regional_pair"] == "eastus"


def test_generate_mirror_urls():
    regions = [
        {"name": "eastus", "regional_pair": "westus2"},
        {"name": "westus2", "regional_pair": "eastus"},
    ]
    mirrors = am.generate_mirror_urls(regions)

    assert "eastus" in mirrors
    assert mirrors["eastus"]["primary"] == "https://depot.eastus.prod.azure.ciq.com"
    assert mirrors["eastus"]["backup"] == "https://depot.westus2.prod.azure.ciq.com"

    assert "westus2" in mirrors
    assert mirrors["westus2"]["primary"] == "https://depot.westus2.prod.azure.ciq.com"
    assert mirrors["westus2"]["backup"] == "https://depot.eastus.prod.azure.ciq.com"


def test_transform_azure_mirrors(tmp_path):
    # Create temporary test files
    metadata_file = tmp_path / "test_metadata.yaml"
    mirrors_file = tmp_path / "test_mirrors.yaml"
    output_file = tmp_path / "test_output.yaml"

    # Write test data
    metadata = {
        "Regions": [
            {"name": "eastus", "regional_pair": "westus2"},
            {"name": "westus2", "regional_pair": "eastus"},
        ]
    }
    existing_mirrors = {
        "azure": {"default": {"primary": "https://depot.eastus.prod.azure.ciq.com"}}
    }

    with open(metadata_file, "w") as f:
        yaml.dump(metadata, f)
    with open(mirrors_file, "w") as f:
        yaml.dump(existing_mirrors, f)

    # Run transformation
    result = am.transform_azure_mirrors(
        str(metadata_file), str(mirrors_file), str(output_file)
    )

    # Verify results
    assert "azure" in result
    assert "default" in result["azure"]
    assert "eastus" in result["azure"]
    assert "westus2" in result["azure"]
    assert (
        result["azure"]["eastus"]["primary"]
        == "https://depot.eastus.prod.azure.ciq.com"
    )
    assert (
        result["azure"]["eastus"]["backup"]
        == "https://depot.westus2.prod.azure.ciq.com"
    )


def test_transform_azure_mirrors_error_handling():
    with pytest.raises(FileNotFoundError):
        am.transform_azure_mirrors(
            "nonexistent_metadata.yaml", "nonexistent_mirrors.yaml"
        )


def test_parse_args_defaults():
    """Test parse_args with default arguments."""
    args = am.parse_args([])
    assert args.metadata == "azure.metadata.yaml"
    assert args.mirrors == "src/rlc_cloud_repos/data/ciq-mirrors.yaml"
    assert args.output is None
    assert not args.verify


def test_parse_args_with_values():
    """Test parse_args with custom values."""
    args = am.parse_args(
        [
            "--metadata",
            "custom.yaml",
            "--mirrors",
            "mirrors.yaml",
            "--output",
            "out.yaml",
            "--verify",
        ]
    )
    assert args.metadata == "custom.yaml"
    assert args.mirrors == "mirrors.yaml"
    assert args.output == "out.yaml"
    assert args.verify


def test_main_success(tmp_path):
    """Test main function with valid files."""
    metadata_file = tmp_path / "metadata.yaml"
    mirrors_file = tmp_path / "mirrors.yaml"

    # Create test files
    metadata = {"Regions": [{"name": "eastus", "regional_pair": "westus2"}]}
    mirrors = {
        "azure": {"default": {"primary": "https://depot.eastus.prod.azure.ciq.com"}}
    }

    with open(metadata_file, "w") as f:
        yaml.dump(metadata, f)
    with open(mirrors_file, "w") as f:
        yaml.dump(mirrors, f)

    result = am.main(["--metadata", str(metadata_file), "--mirrors", str(mirrors_file)])
    assert result == 0


def test_main_verify_mode(tmp_path):
    """Test main function in verify mode."""
    metadata_file = tmp_path / "metadata.yaml"
    mirrors_file = tmp_path / "mirrors.yaml"

    # Create test files with different content
    metadata = {"Regions": [{"name": "eastus", "regional_pair": "westus2"}]}
    mirrors = {"azure": {"default": {"primary": "https://old.url.com"}}}

    with open(metadata_file, "w") as f:
        yaml.dump(metadata, f)
    with open(mirrors_file, "w") as f:
        yaml.dump(mirrors, f)

    result = am.main(
        ["--metadata", str(metadata_file), "--mirrors", str(mirrors_file), "--verify"]
    )
    assert result == 1


def test_main_verify_mode_no_change(tmp_path):
    """Test main function in verify mode."""
    metadata_file = tmp_path / "metadata.yaml"
    mirrors_file = tmp_path / "mirrors.yaml"

    # Create test files with different content
    metadata = {"Regions": [{"name": "eastus", "regional_pair": "westus2"}]}
    mirrors = {
        "azure": {
            "eastus": {
                "primary": "https://depot.eastus.prod.azure.ciq.com",
                "backup": "https://depot.westus2.prod.azure.ciq.com",
            },
            "default": {
                "primary": "https://depot.eastus.prod.azure.ciq.com",
                "backup": "https://depot.westus2.prod.azure.ciq.com",
            },
        }
    }

    with open(metadata_file, "w") as f:
        yaml.dump(metadata, f)
    with open(mirrors_file, "w") as f:
        yaml.dump(mirrors, f)

    result = am.main(
        ["--metadata", str(metadata_file), "--mirrors", str(mirrors_file), "--verify"]
    )
    assert result == 0


def test_main_error_handling():
    """Test main function with invalid files."""
    result = am.main(["--metadata", "nonexistent.yaml"])
    assert result == 1
