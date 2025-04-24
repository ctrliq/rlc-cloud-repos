import urllib.request
from pprint import pformat

import pytest

from rlc.cloud_repos.repo_config import load_mirror_map, select_mirror


def test_load_mirror_map_success(mirrors_file):
    """Test successful loading of mirror map."""
    mirror_map = load_mirror_map(str(mirrors_file))
    assert isinstance(mirror_map, dict)
    assert "azure" in mirror_map
    assert "default" in mirror_map


def test_load_mirror_map_file_not_found():
    """Test load_mirror_map with nonexistent file."""
    with pytest.raises(FileNotFoundError):
        load_mirror_map("nonexistent.yaml")


def test_load_mirror_map_invalid_yaml(tmp_path):
    """Test load_mirror_map with invalid YAML."""
    invalid_yaml = tmp_path / "invalid.yaml"
    invalid_yaml.write_text("{ invalid: yaml: content")
    with pytest.raises(ValueError):
        load_mirror_map(str(invalid_yaml))


@pytest.mark.parametrize(
    "provider,region",
    [
        ("azure", "eastus"),
        ("azure", "westus2"),
        ("azure", "nonexistent-region"),
        ("gcp", "us-central1"),
        ("oracle", "us-ashburn-1"),
        ("unknown-provider", "unknown-region"),
    ],
)
def test_select_mirror_returns_non_empty_urls(mirrors_file, provider, region):
    """Test select_mirror always returns two non-empty URLs."""
    mirror_map = load_mirror_map(str(mirrors_file))

    primary, backup = select_mirror(
        {"provider": provider, "region": region}, mirror_map
    )

    assert isinstance(primary, str)
    assert isinstance(backup, str)
    assert primary != ""
    assert primary.startswith("https://")


def test_select_mirror_provider_fallback(mirrors_file):
    """Test select_mirror falls back to provider default."""
    mirror_map = load_mirror_map(str(mirrors_file))

    primary, backup = select_mirror(
        {"provider": "azure", "region": "unknown"}, mirror_map
    )
    assert primary == "https://depot.eastus.prod.azure.ciq.com"


def test_select_mirror_global_fallback(mirrors_file):
    """Test select_mirror falls back to global default."""
    mirror_map = load_mirror_map(str(mirrors_file))

    primary, backup = select_mirror(
        {"provider": "unknown", "region": "unknown"}, mirror_map
    )
    assert primary == "https://depot.eastus.prod.azure.ciq.com"


def test_select_mirror_no_fallback():
    """Test select_mirror raises error when no fallback exists."""
    mirror_map = {"azure": {"eastus": {"primary": "url"}}}  # No default entry

    with pytest.raises(ValueError):
        select_mirror({"provider": "unknown", "region": "unknown"}, mirror_map)


# =====================================================================
# ================= THIS IS A TEST FOR THE DATA FILE ==================
# =====================================================================


def test_metadata_file_for_missing_values(mirrors_file):
    mirror_map = load_mirror_map(str(mirrors_file))

    # The mirror map must provide a default provider section with primary and backup values
    assert "default" in mirror_map, "No default section found in the mirror map"
    assert "primary" in mirror_map["default"], "No primary URL found in default section"
    assert "backup" in mirror_map["default"], "No backup URL found in default section"
    mirror_map.pop("default")

    for key, value in mirror_map.items():
        # Each provider must provide a default with primary and backup values
        assert "default" in value, f"No default section found in provider '{key}'"
        assert (
            "primary" in value["default"]
        ), f"No primary URL found in default section of provider '{key}'"
        assert (
            "backup" in value["default"]
        ), f"No backup URL found in default section of provider '{key}'"
        value.pop("default")
        for region, r_map in value.items():
            assert (
                "primary" in r_map
            ), f"No primary URL found in region '{region}' of provider '{key}'"
            assert (
                "backup" in r_map
            ), f"No backup URL found in region '{region}' of provider '{key}'"


# To run this test, specify "-m mirrors_get" in the pytest command line
@pytest.mark.mirrors_get
def test_mirror_urls_retrieval(mirrors_file):  # pragma: no cover
    """Test that all unique mirror URLs starting with https:// are retrievable."""
    mirror_map = load_mirror_map(str(mirrors_file))
    extra_path = "/public/files/rlc-9/rlc-extras-9.x86_64/repodata/repomd.xml"

    # Collect all unique URLs starting with https://
    unique_urls = set()
    for provider, provider_data in mirror_map.items():
        for region, region_data in provider_data.items():
            if isinstance(region_data, dict):
                primary = region_data.get("primary", "")
                backup = region_data.get("backup", "")
                if primary.startswith("https://"):
                    unique_urls.add(primary)
                if backup.startswith("https://"):
                    unique_urls.add(backup)

    # Test retrieval of each URL using urllib
    failed_urls = []
    for url in sorted(unique_urls):
        try:
            with urllib.request.urlopen(url + extra_path, timeout=5) as response:
                if response.status != 200:
                    failed_urls.append((url, response.status))
        except Exception as e:
            failed_urls.append((url, str(e)))

    # Using pprint
    assert not failed_urls, f"Failed to retrieve URLs:\n{pformat(failed_urls)}"
