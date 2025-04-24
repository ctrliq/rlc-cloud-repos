# tests/conftest.py
import shutil
import sys
from pathlib import Path

import pytest


@pytest.fixture
def dnf_vars_dir(tmp_path, monkeypatch):
    """Fixture to mock DNF_VARS_DIR to use a temp directory."""
    dnf_path = tmp_path / "dnf" / "vars"
    dnf_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("rlc.cloud_repos.main.DNF_VARS_DIR", str(dnf_path))
    return dnf_path


@pytest.fixture
def marker(tmp_path, monkeypatch):
    """Fixture to mock MARKERFILE to use a temp file."""
    marker_path = tmp_path / ".configured"
    monkeypatch.setattr("rlc.cloud_repos.main.MARKERFILE", str(marker_path))
    yield marker_path


@pytest.fixture
def mirrors_file(tmp_path, monkeypatch):
    """Fixture to create a temporary mirrors file."""
    mirrors_path = tmp_path / "mirrors.yaml"

    # Copy the content from the package data to mirrors.yaml
    source_path = Path(__file__).parent.parent / "data/ciq-mirrors.yaml"
    shutil.copy(source_path, mirrors_path)

    monkeypatch.setattr("rlc.cloud_repos.main.DEFAULT_MIRROR_PATH", str(mirrors_path))
    yield mirrors_path


def _replace_command(tmp_path, command, contents):
    """Helper function to replace a command."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script_path = bin_dir / command

    script_path.write_text(contents)
    script_path.chmod(0o755)  # Make the script executable
    return script_path


@pytest.fixture
def cloud_init(tmp_path):
    """Fixture to create a mock cloud-init command script."""

    script_content = """#!/bin/sh
if [ "$2" = "cloud_name" ]; then
    echo "aws"
elif [ "$2" = "region" ]; then
    echo "us-east-2"
else
    exit 1
fi
"""
    yield _replace_command(tmp_path, "cloud-init", script_content)


@pytest.fixture
def broken_cloud_init(tmp_path):
    """Fixture to create a mock cloud-init command script that fails."""
    script_content = """#!/bin/sh
exit 1
"""
    yield _replace_command(tmp_path, "cloud-init", script_content)


@pytest.fixture
def mock_root(monkeypatch):
    """Fixture to mock root user permissions."""
    monkeypatch.setattr("os.geteuid", lambda: 0)


# Add the "src" directories to the import path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cloud-repos"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "framework"))
