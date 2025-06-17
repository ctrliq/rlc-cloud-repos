from unittest.mock import MagicMock

import pytest

from rlc.cloud_repos.dnf_vars import BACKUP_SUFFIX, write_dnf_var


@pytest.fixture
def dnf_dir(tmp_path):
    """Create a temporary DNF vars directory"""
    vars_dir = tmp_path / "dnf" / "vars"
    vars_dir.mkdir(parents=True)
    yield vars_dir


def test_write_dnf_var_new_file(dnf_dir):
    """Test writing a DNF var to a new file"""
    write_dnf_var(dnf_dir, "test", "value")
    path = dnf_dir / "test"
    assert path.exists()
    assert path.read_text().strip() == "value"


def test_write_dnf_var_new_file_nooverwrite(dnf_dir):
    """Test writing a DNF var to a new file"""
    write_dnf_var(dnf_dir, "test", "value", overwrite=False)
    path = dnf_dir / "test"
    assert path.exists()
    assert path.read_text().strip() == "value"


def test_write_dnf_var_existing_same_value(dnf_dir):
    """Test writing a DNF var when file exists with same value"""
    path = dnf_dir / "test"
    path.write_text("value\n")

    write_dnf_var(dnf_dir, "test", "value")
    assert path.exists()
    assert not (path.parent / f"test{BACKUP_SUFFIX}").exists()
    assert path.read_text().strip() == "value"


def test_write_dnf_var_existing_different_value(dnf_dir):
    """Test writing a DNF var when file exists with different value"""
    path = dnf_dir / "test"
    path.write_text("old_value\n")

    write_dnf_var(dnf_dir, "test", "new_value")
    assert path.exists()
    assert (path.parent / f"test{BACKUP_SUFFIX}").exists()
    assert path.read_text().strip() == "new_value"
    assert (path.parent / f"test{BACKUP_SUFFIX}").read_text().strip() == "old_value"


def test_write_dnf_var_existing_different_value_nooverwrite(dnf_dir):
    """Test writing a DNF var when file exists with different value"""
    path = dnf_dir / "test"
    path.write_text("old_value\n")

    write_dnf_var(dnf_dir, "test", "new_value", overwrite=False)
    assert path.exists()
    assert not (path.parent / f"test{BACKUP_SUFFIX}").exists()
    assert path.read_text().strip() == "old_value"


def test_write_dnf_var_non_writable_dir_non_existent_file(monkeypatch, dnf_dir, caplog):
    """Test writing DNF var to a non-writable directory."""
    # Make directory "read-only"
    monkeypatch.setattr(
        "pathlib.Path.write_text",
        MagicMock(side_effect=PermissionError("Permission denied")),
    )

    write_dnf_var(dnf_dir, "test", "value")

    # Verify error was logged
    assert "Cannot write to DNF var 'test'" in caplog.text
    assert "Permission denied" in caplog.text


def test_write_dnf_var_non_writable_dir_pre_existing_file(monkeypatch, dnf_dir, caplog):
    """Test writing DNF var to a non-writable directory."""
    # Make directory read-only
    write_dnf_var(dnf_dir, "test", "pre-value")

    monkeypatch.setattr(
        "pathlib.Path.rename",
        MagicMock(side_effect=PermissionError("Permission denied")),
    )

    write_dnf_var(dnf_dir, "test", "value")

    # Verify error was logged
    assert "Cannot backup DNF var 'test'" in caplog.text
    assert "Permission denied" in caplog.text
