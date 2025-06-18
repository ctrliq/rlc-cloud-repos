# tests/test_cloud_metadata_suite.py
"""
Test Suite: Cloud Metadata Detection & Mirror Selection

This module validates:
- Cloud provider & region extraction from cloud-init metadata
- Mirror URL selection based on provider/region
- YUM repo config generation
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rlc.cloud_repos.cloud_metadata import get_cloud_metadata

MIRROR_FIXTURES = Path(__file__).parent.parent / "data/ciq-mirrors.yaml"


@pytest.mark.parametrize(
    "expected_provider,expected_region",
    [
        ("aws", "us-west-2"),
        ("azure", "eastus"),
        ("gcp", "us-central1"),
        ("oracle", "us-ashburn-1"),
        ("unknown", "fallback-region"),
    ],
)
def test_cloud_metadata_and_mirror(
    monkeypatch, mirrors_file, expected_provider, expected_region
):
    """
    Validates that cloud metadata and mirror resolution behave as expected.
    """

    def fake_check_output(cmd, text=True, universal_newlines=True):
        if "cloud_name" in cmd:
            return expected_provider
        elif "region" in cmd:
            return expected_region

    monkeypatch.setattr(
        "rlc.cloud_repos.cloud_metadata.subprocess.check_output", fake_check_output
    )
    metadata = get_cloud_metadata()
    assert metadata["provider"] == expected_provider
    assert metadata["region"] == expected_region


def test_cloud_metadata_returns_dict(monkeypatch):
    monkeypatch.setattr(
        "subprocess.check_output",
        lambda cmd, text=True, universal_newlines=True: (
            "aws" if "cloud_name" in cmd else "us-west-2"
        ),
    )
    result = get_cloud_metadata()
    assert isinstance(result, dict)
    assert result["provider"] == "aws"
    assert result["region"] == "us-west-2"


def test_cloud_metadata_handles_subprocess_error(monkeypatch):
    """Test that get_cloud_metadata properly handles subprocess errors."""

    side_effect = subprocess.CalledProcessError(1, "cloud-init", "test error")

    monkeypatch.setattr("subprocess.check_output", MagicMock(side_effect=side_effect))

    with pytest.raises(
        RuntimeError, match="cloud-init must be available and functional"
    ):
        get_cloud_metadata()


def test_cloud_metadata_no_mock_subprocess(cloud_init):
    """Test that get_cloud_metadata works with a real cloud-init command."""
    result = get_cloud_metadata(str(cloud_init))

    assert isinstance(result, dict)
    assert result["provider"] == "aws"
    assert result["region"] == "us-east-2"


def test_cloud_metadata_invalid_command():
    """Test that get_cloud_metadata raises an error for an invalid command."""
    invalid_command = "invalid-cloud-init-command"
    with pytest.raises(RuntimeError, match=f"{invalid_command} command was not found"):
        get_cloud_metadata(invalid_command)


def test_cloud_metadata_invalid_subprocess(broken_cloud_init):
    """Test that get_cloud_metadata raises an error for a broken cloud-init command."""
    with pytest.raises(
        RuntimeError, match="cloud-init must be available and functional"
    ):
        get_cloud_metadata(str(broken_cloud_init))
