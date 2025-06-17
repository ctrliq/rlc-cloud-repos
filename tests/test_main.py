from functools import partial
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rlc.cloud_repos.cloud_metadata import get_cloud_metadata
from rlc.cloud_repos.main import _configure_repos, main, parse_args

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# @pytest.fixture(autouse=True)
# def mock_get_cloud_metadata(monkeypatch, request):
#     if "test_cloud_metadata_suite" not in request.node.nodeid:
#         monkeypatch.setattr(
#             "rlc.cloud_repos.main.get_cloud_metadata",
#             lambda: {"provider": "mock", "region": "mock-region"},
#         )


@pytest.fixture
def cloud_metadata_mock(monkeypatch, cloud_init, mirrors_file):
    monkeypatch.setattr(
        "rlc.cloud_repos.main.get_cloud_metadata",
        partial(get_cloud_metadata, str(cloud_init)),
    )


def test_parse_args_default():
    """Test parse_args with default arguments."""
    args = parse_args([])
    assert args.mirror_file is None
    assert not args.force


def test_parse_args_with_values():
    """Test parse_args with specific values."""
    args = parse_args(["--mirror-file", "test.yaml", "--force"])
    assert args.mirror_file == "test.yaml"
    assert args.force


def test_main_with_force_flag(
    tmp_path, dnf_vars_dir, marker, mirrors_file, cloud_metadata_mock, mock_root
):
    """Test main function with force flag bypasses marker check."""
    marker.touch()
    initial_mtime = marker.stat().st_mtime

    result = main(["--force"])
    assert result == 0
    assert marker.stat().st_mtime > initial_mtime

    assert (
        dnf_vars_dir / "baseurl1"
    ).read_text().strip() == "https://depot-us-east-1.s3.us-east-1.amazonaws.com"


def test_main_respects_marker_file(marker, mock_root):
    """Test main respects existing marker file."""
    marker.touch()
    initial_mtime = marker.stat().st_mtime

    result = main([])
    assert result == 0
    assert marker.stat().st_mtime == initial_mtime


def test_main_creates_marker_file(dnf_vars_dir, marker, cloud_metadata_mock, mock_root):
    """Test main creates marker file after successful run."""
    result = main([])
    assert result == 0
    assert marker.exists()

    assert (
        dnf_vars_dir / "baseurl1"
    ).read_text().strip() == "https://depot-us-east-1.s3.us-east-1.amazonaws.com"


def test_main_with_custom_mirror_file(
    dnf_vars_dir, marker, mirrors_file, cloud_metadata_mock, mock_root
):
    """Test main with custom mirror file path."""
    result = main(["--mirror-file", str(mirrors_file)])
    assert result == 0

    assert (
        dnf_vars_dir / "baseurl1"
    ).read_text().strip() == "https://depot-us-east-1.s3.us-east-1.amazonaws.com"


def test_main_handles_configuration_error(monkeypatch, mock_root):
    """Test main handles configuration errors gracefully."""
    monkeypatch.setattr(
        "rlc.cloud_repos.main._configure_repos",
        lambda x: (_ for _ in ()).throw(Exception("Test error")),
    )
    result = main(["--force"])
    assert result == 1


def test_configure_repos_writes_touchfile(
    tmp_path, dnf_vars_dir, marker, mirrors_file, cloud_metadata_mock
):
    """Test _configure_repos writes marker file."""
    _configure_repos(str(mirrors_file))
    assert marker.exists()
    assert "Configured on" in marker.read_text()
    assert (
        dnf_vars_dir / "baseurl1"
    ).read_text().strip() == "https://depot-us-east-1.s3.us-east-1.amazonaws.com"


def test_configure_repos_invalid_mirror_file(cloud_metadata_mock):
    """Test _configure_repos with invalid mirror file."""
    with pytest.raises(Exception):
        _configure_repos("nonexistent.yaml")


def test_configure_repos_test_overwrite_preexisting_file(
    dnf_vars_dir, mirrors_file, marker, cloud_metadata_mock
):
    """Test _configure_repos with test overwrite and pre-existing file."""

    # Create a temporary file to simulate the existing file
    existing_file1 = dnf_vars_dir / "baseurl1"
    existing_file1.write_text("old_value1")
    existing_file2 = dnf_vars_dir / "baseurl2"
    existing_file2.write_text("old_value2")

    # Call the function with test overwrite
    _configure_repos(str(mirrors_file))

    # Check that the existing file was modified
    assert (
        existing_file1.read_text().strip()
        == "https://depot-us-east-1.s3.us-east-1.amazonaws.com"
    )
    assert (
        existing_file2.read_text().strip()
        == "https://depot-us-west-2.s3.us-west-2.amazonaws.com"
    )


def test_configure_repos_test_no_overwrite_preexisting_file(
    monkeypatch, tmp_path, dnf_vars_dir, marker, mirrors_file
):
    """Test _configure_repos with test overwrite and no pre-existing file."""

    # Create a temporary file to simulate the existing file
    existing_file1 = dnf_vars_dir / "baseurl1"
    existing_file1.write_text("old_value1")
    existing_file2 = dnf_vars_dir / "baseurl2"
    existing_file2.write_text("old_value2")

    bad_get_cloud_metadata = MagicMock(side_effect=Exception("Test error"))
    monkeypatch.setattr(
        "rlc.cloud_repos.main.get_cloud_metadata", bad_get_cloud_metadata
    )

    # Call the function with test overwrite
    _configure_repos(str(mirrors_file))

    # Check that the existing file was not modified
    assert existing_file1.read_text().strip() == "old_value1"
    assert existing_file2.read_text().strip() == "old_value2"


def test_configure_repos_test_no_overwrite_no_preexisting_file(
    monkeypatch, tmp_path, dnf_vars_dir, marker, mirrors_file
):
    """Test _configure_repos with test overwrite and no pre-existing file."""

    # Create a temporary file to simulate the existing file
    file1 = dnf_vars_dir / "baseurl1"
    file2 = dnf_vars_dir / "baseurl2"

    # Call the function with test overwrite
    _configure_repos(str(mirrors_file))

    # Check that the existing file was not modified
    assert file1.exists()
    assert file2.exists()

    # These should be the default values from the mirrors.yaml file.
    assert file1.read_text().strip() == "https://depot.eastus.prod.azure.ciq.com"
    assert file2.read_text().strip() == "https://depot.westus2.prod.azure.ciq.com"


def test_main_requires_root():
    """Test that the program exits if not run as root."""
    with patch("os.geteuid", return_value=1000):  # Non-root UID
        assert main([]) == 1


def test_main_with_env_overrides(
    monkeypatch, dnf_vars_dir, marker, mirrors_file, mock_root
):
    """
    Test main() with DEBUG_RCR_PROVIDER and DEBUG_RCR_REGION environment variables set.
    This exercises the code path where provider/region overrides are used.
    """
    # do setup: set environment variables for provider and region
    monkeypatch.setenv("DEBUG_RCR_PROVIDER", "aws")
    monkeypatch.setenv("DEBUG_RCR_REGION", "us-east-1")

    # perform test operation: call main
    result = main(["--mirror-file", str(mirrors_file)])
    # assert expected result: main returns 0 and DNF vars are set for the override
    assert result == 0
    assert (
        dnf_vars_dir / "baseurl1"
    ).read_text().strip() == "https://depot-us-east-1.s3.us-east-1.amazonaws.com"
