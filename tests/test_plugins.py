"""
Unit tests for the plugins module.
"""

import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from rlc.cloud_repos import plugins


class TestPluginDiscovery(unittest.TestCase):
    """Test plugin discovery and validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("rlc.cloud_repos.plugins.PLUGINS_DIR")
    def test_discover_plugins_empty_directory(self, mock_plugins_dir):
        """Test plugin discovery in empty directory."""
        mock_plugins_dir.__str__ = Mock(return_value=str(self.plugins_dir))

        with patch("rlc.cloud_repos.plugins.Path") as mock_path:
            mock_path.return_value = self.plugins_dir
            result = plugins.discover_plugins()

        self.assertEqual(result, [])

    @patch("rlc.cloud_repos.plugins.PLUGINS_DIR")
    def test_discover_plugins_nonexistent_directory(self, mock_plugins_dir):
        """Test plugin discovery when directory doesn't exist."""
        nonexistent_dir = Path(self.temp_dir) / "nonexistent"
        mock_plugins_dir.__str__ = Mock(return_value=str(nonexistent_dir))

        with patch("rlc.cloud_repos.plugins.Path") as mock_path:
            mock_path.return_value = nonexistent_dir
            result = plugins.discover_plugins()

        self.assertEqual(result, [])

    @patch("rlc.cloud_repos.plugins.PLUGINS_DIR")
    def test_discover_plugins_path_is_file_not_directory(self, mock_plugins_dir):
        """Test plugin discovery when PLUGINS_DIR path is a file, not directory."""
        # Create a file instead of a directory
        file_path = self.plugins_dir / "not_a_directory"
        file_path.write_text("I'm a file, not a directory")
        mock_plugins_dir.__str__ = Mock(return_value=str(file_path))

        with patch("rlc.cloud_repos.plugins.Path") as mock_path:
            mock_path.return_value = file_path
            result = plugins.discover_plugins()

        self.assertEqual(result, [])

    @patch("rlc.cloud_repos.plugins.PLUGINS_DIR")
    def test_discover_plugins_filters_valid_plugins(self, mock_plugins_dir):
        """Test that discover_plugins only returns plugins that pass is_safe_plugin."""
        mock_plugins_dir.__str__ = Mock(return_value=str(self.plugins_dir))
        valid_plugin = Mock()
        valid_plugin.is_file.return_value = True
        invalid_plugin = Mock()
        invalid_plugin.is_file.return_value = True
        directory = Mock()
        directory.is_file.return_value = False

        with patch("rlc.cloud_repos.plugins.Path") as mock_path, patch(
            "rlc.cloud_repos.plugins.is_safe_plugin"
        ) as mock_is_safe:
            mock_plugins_path = Mock()
            mock_plugins_path.exists.return_value = True
            mock_plugins_path.is_dir.return_value = True
            mock_plugins_path.iterdir.return_value = [
                valid_plugin,
                invalid_plugin,
                directory,
            ]
            mock_path.return_value = mock_plugins_path

            # Only valid_plugin passes safety check
            mock_is_safe.side_effect = lambda p: p == valid_plugin

            result = plugins.discover_plugins()

        self.assertEqual(result, [valid_plugin])

    @patch("rlc.cloud_repos.plugins.PLUGINS_DIR")
    def test_discover_plugins_sorts_results(self, mock_plugins_dir):
        """Test that discover_plugins returns results sorted by name."""
        mock_plugins_dir.__str__ = Mock(return_value=str(self.plugins_dir))

        # Create mock plugins with sortable names
        plugin_z = Mock()
        plugin_z.is_file.return_value = True
        plugin_z.name = "z.sh"
        plugin_z.__lt__ = lambda self, other: self.name < other.name

        plugin_a = Mock()
        plugin_a.is_file.return_value = True
        plugin_a.name = "a.sh"
        plugin_a.__lt__ = lambda self, other: self.name < other.name

        plugin_m = Mock()
        plugin_m.is_file.return_value = True
        plugin_m.name = "m.sh"
        plugin_m.__lt__ = lambda self, other: self.name < other.name

        with patch("rlc.cloud_repos.plugins.Path") as mock_path, patch(
            "rlc.cloud_repos.plugins.is_safe_plugin", return_value=True
        ):
            mock_plugins_path = Mock()
            mock_plugins_path.exists.return_value = True
            mock_plugins_path.is_dir.return_value = True
            mock_plugins_path.iterdir.return_value = [plugin_z, plugin_a, plugin_m]
            mock_path.return_value = mock_plugins_path

            result = plugins.discover_plugins()

        # Should be sorted by name
        expected = [plugin_a, plugin_m, plugin_z]
        self.assertEqual(result, expected)

    @patch("rlc.cloud_repos.plugins.PLUGINS_DIR")
    def test_discover_plugins_processes_all_files(self, mock_plugins_dir):
        """Test that discover_plugins processes all files in directory."""
        mock_plugins_dir.__str__ = Mock(return_value=str(self.plugins_dir))

        with patch("rlc.cloud_repos.plugins.Path") as mock_path:
            mock_plugins_path = Mock()
            mock_plugins_path.exists.return_value = True
            mock_plugins_path.is_dir.return_value = True
            mock_plugins_path.iterdir.return_value = []
            mock_path.return_value = mock_plugins_path

            plugins.discover_plugins()

        # Verify iterdir was called to get all files
        mock_plugins_path.iterdir.assert_called_once()

    @patch("rlc.cloud_repos.plugins.PLUGINS_DIR")
    def test_discover_plugins_glob_exception(self, mock_plugins_dir):
        """Test plugin discovery handles glob exceptions gracefully."""
        mock_plugins_dir.__str__ = Mock(return_value=str(self.plugins_dir))

        with patch("rlc.cloud_repos.plugins.Path") as mock_path:
            mock_path.return_value = self.plugins_dir
            # Mock glob to raise an exception
            mock_glob = Mock()
            mock_glob.glob.side_effect = OSError("Permission denied")
            mock_path.return_value = mock_glob

            result = plugins.discover_plugins()

        self.assertEqual(result, [])

    def test_is_safe_plugin_valid(self):
        """Test plugin validation for a valid plugin."""
        plugin_file = self.plugins_dir / "test.sh"
        plugin_file.write_text("#!/bin/bash\necho test")
        plugin_file.chmod(0o755)

        with patch("pathlib.Path.stat") as mock_stat, patch(
            "os.access", return_value=True
        ):
            mock_stat_result = Mock()
            mock_stat_result.st_uid = 0
            mock_stat_result.st_mode = stat.S_IFREG | 0o755
            mock_stat.return_value = mock_stat_result

            result = plugins.is_safe_plugin(plugin_file)

        self.assertTrue(result)

    def test_is_safe_plugin_world_writable(self):
        """Test plugin validation rejects world-writable files."""
        plugin_file = self.plugins_dir / "test.sh"
        plugin_file.write_text("#!/bin/bash\necho test")
        plugin_file.chmod(0o777)

        with patch("pathlib.Path.stat") as mock_stat, patch(
            "os.access", return_value=True
        ):
            mock_stat_result = Mock()
            mock_stat_result.st_uid = 0
            mock_stat_result.st_mode = stat.S_IFREG | 0o777
            mock_stat.return_value = mock_stat_result

            result = plugins.is_safe_plugin(plugin_file)

        self.assertFalse(result)

    def test_is_safe_plugin_non_root_owned(self):
        """Test plugin validation rejects non-root owned files."""
        plugin_file = self.plugins_dir / "test.sh"
        plugin_file.write_text("#!/bin/bash\necho test")
        plugin_file.chmod(0o755)

        with patch("pathlib.Path.stat") as mock_stat, patch(
            "os.access", return_value=True
        ):
            mock_stat_result = Mock()
            mock_stat_result.st_uid = 1000  # non-root
            mock_stat_result.st_mode = stat.S_IFREG | 0o755
            mock_stat.return_value = mock_stat_result

            result = plugins.is_safe_plugin(plugin_file)

        self.assertFalse(result)

    def test_is_safe_plugin_not_executable(self):
        """Test plugin validation rejects non-executable files."""
        plugin_file = self.plugins_dir / "test.sh"
        plugin_file.write_text("#!/bin/bash\necho test")
        plugin_file.chmod(0o644)

        with patch("pathlib.Path.stat") as mock_stat, patch(
            "os.access", return_value=False
        ):
            mock_stat_result = Mock()
            mock_stat_result.st_uid = 0
            mock_stat_result.st_mode = stat.S_IFREG | 0o644
            mock_stat.return_value = mock_stat_result

            result = plugins.is_safe_plugin(plugin_file)

        self.assertFalse(result)

    def test_is_safe_plugin_ignores_disabled_files(self):
        """Test plugin validation ignores files with disable patterns."""
        disabled_files = [
            "test.disabled",
            "test.ignore",
            "test.bak",
            "test.rpmnew",
            "test.backup",
        ]

        for filename in disabled_files:
            plugin_file = self.plugins_dir / filename
            plugin_file.write_text("#!/bin/bash\necho test")
            plugin_file.chmod(0o755)

            with patch("pathlib.Path.stat") as mock_stat, patch(
                "os.access", return_value=True
            ):
                mock_stat_result = Mock()
                mock_stat_result.st_uid = 0
                mock_stat_result.st_mode = stat.S_IFREG | 0o755
                mock_stat.return_value = mock_stat_result

                result = plugins.is_safe_plugin(plugin_file)

            self.assertFalse(result, f"File {filename} should be ignored")

    def test_is_safe_plugin_accepts_various_extensions(self):
        """Test plugin validation accepts files with various extensions and no extension."""
        valid_files = [
            "plugin-shell",  # no extension
            "plugin.py",  # Python
            "plugin.pl",  # Perl
            "plugin.go",  # Go binary
            "plugin.rb",  # Ruby
        ]

        for filename in valid_files:
            plugin_file = self.plugins_dir / filename
            plugin_file.write_text("#!/bin/bash\necho test")
            plugin_file.chmod(0o755)

            with patch("pathlib.Path.stat") as mock_stat, patch(
                "os.access", return_value=True
            ):
                mock_stat_result = Mock()
                mock_stat_result.st_uid = 0
                mock_stat_result.st_mode = stat.S_IFREG | 0o755
                mock_stat.return_value = mock_stat_result

                result = plugins.is_safe_plugin(plugin_file)

            self.assertTrue(result, f"File {filename} should be accepted")

    def test_is_safe_plugin_empty_file(self):
        """Test plugin validation accepts empty files (content doesn't matter)."""
        plugin_file = self.plugins_dir / "test.sh"
        plugin_file.write_text("")  # empty file
        plugin_file.chmod(0o755)

        with patch("pathlib.Path.stat") as mock_stat, patch(
            "os.access", return_value=True
        ):
            mock_stat_result = Mock()
            mock_stat_result.st_uid = 0
            mock_stat_result.st_mode = stat.S_IFREG | 0o755
            mock_stat.return_value = mock_stat_result

            result = plugins.is_safe_plugin(plugin_file)

        self.assertTrue(result)

    def test_is_safe_plugin_not_regular_file(self):
        """Test plugin validation rejects non-regular files (directories, symlinks)."""
        # Create a directory instead of a file
        plugin_dir = self.plugins_dir / "test.sh"
        plugin_dir.mkdir()

        result = plugins.is_safe_plugin(plugin_dir)
        self.assertFalse(result)

    def test_is_safe_plugin_access_check_error(self):
        """Test plugin validation handles os.access errors gracefully."""
        plugin_file = self.plugins_dir / "test.sh"
        plugin_file.write_text("#!/bin/bash\necho test")
        plugin_file.chmod(0o755)

        # Mock successful stat but failing access check
        with patch("pathlib.Path.stat") as mock_stat, patch(
            "os.access", side_effect=OSError("Access check failed")
        ):
            mock_stat_result = Mock()
            mock_stat_result.st_uid = 0  # root
            mock_stat_result.st_mode = stat.S_IFREG | 0o755
            mock_stat.return_value = mock_stat_result

            result = plugins.is_safe_plugin(plugin_file)

        self.assertFalse(result)

    def test_is_safe_plugin_stat_error(self):
        """Test plugin validation handles stat errors gracefully."""
        plugin_file = self.plugins_dir / "test.sh"
        plugin_file.write_text("#!/bin/bash\necho test")

        # Mock failing stat
        with patch.object(Path, "stat", side_effect=OSError("Stat failed")):
            result = plugins.is_safe_plugin(plugin_file)

        self.assertFalse(result)


class TestPluginExecution(unittest.TestCase):
    """Test plugin execution and variable parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.plugin_path = Path(self.temp_dir) / "test.sh"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("rlc.cloud_repos.plugins.PLUGIN_TIMEOUT", 5)
    def test_execute_plugin_success(self):
        """Test successful plugin execution."""
        # Mock subprocess.run to return successful execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "custom_var=test_value\nother_var=other_value\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            success, variables = plugins.execute_plugin(
                self.plugin_path, "aws", "us-east-1", "http://primary", "http://backup"
            )

        self.assertTrue(success)
        self.assertEqual(
            variables, {"custom_var": "test_value", "other_var": "other_value"}
        )

        # Verify subprocess was called with correct arguments
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(
            args[1:],
            [
                "--provider",
                "aws",
                "--region",
                "us-east-1",
                "--primary-url",
                "http://primary",
                "--backup-url",
                "http://backup",
            ],
        )

    @patch("rlc.cloud_repos.plugins.PLUGIN_TIMEOUT", 5)
    def test_execute_plugin_failure(self):
        """Test plugin execution failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Plugin failed"

        with patch("subprocess.run", return_value=mock_result):
            success, variables = plugins.execute_plugin(
                self.plugin_path, "aws", "us-east-1", "http://primary", "http://backup"
            )

        self.assertFalse(success)
        self.assertEqual(variables, {})

    @patch("rlc.cloud_repos.plugins.PLUGIN_TIMEOUT", 1)
    def test_execute_plugin_timeout(self):
        """Test plugin execution timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired([], 1)):
            success, variables = plugins.execute_plugin(
                self.plugin_path, "aws", "us-east-1", "http://primary", "http://backup"
            )

        self.assertFalse(success)
        self.assertEqual(variables, {})

    def test_execute_plugin_protected_variables_filtered(self):
        """Test that protected variables are filtered out."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "baseurl1=http://blocked\n"
            "custom_var=allowed\n"
            "cloudcontentdir=blocked\n"
            "safe_var=allowed\n"
        )
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            success, variables = plugins.execute_plugin(
                self.plugin_path, "aws", "us-east-1", "http://primary", "http://backup"
            )

        self.assertTrue(success)
        # Protected variables should be filtered out
        self.assertEqual(variables, {"custom_var": "allowed", "safe_var": "allowed"})

    def test_execute_plugin_invalid_variable_names(self):
        """Test that invalid variable names are rejected."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "valid_var=ok\n"
            "invalid-var-with-special-chars!=rejected\n"
            "123_starts_with_number=rejected\n"
            "good_var_name=ok\n"
        )
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            success, variables = plugins.execute_plugin(
                self.plugin_path, "aws", "us-east-1", "http://primary", "http://backup"
            )

        self.assertTrue(success)
        self.assertEqual(variables, {"valid_var": "ok", "good_var_name": "ok"})

    def test_execute_plugin_ignores_comments_and_empty_lines(self):
        """Test that comments and empty lines are ignored."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "# This is a comment\n"
            "\n"
            "valid_var=value1\n"
            "   # Another comment\n"
            "\n"
            "another_var=value2\n"
        )
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            success, variables = plugins.execute_plugin(
                self.plugin_path, "aws", "us-east-1", "http://primary", "http://backup"
            )

        self.assertTrue(success)
        self.assertEqual(variables, {"valid_var": "value1", "another_var": "value2"})

    def test_execute_plugin_ignores_lines_without_equals(self):
        """Test that lines without equals signs are ignored and logged."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "valid_var=value1\n"
            "this line has no equals sign\n"
            "another_var=value2\n"
            "also no equals\n"
        )
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            success, variables = plugins.execute_plugin(
                self.plugin_path, "aws", "us-east-1", "http://primary", "http://backup"
            )

        self.assertTrue(success)
        self.assertEqual(variables, {"valid_var": "value1", "another_var": "value2"})

    def test_execute_plugin_generic_exception(self):
        """Test execute_plugin handles generic exceptions."""
        # Mock subprocess.run to raise a generic exception
        with patch("subprocess.run", side_effect=RuntimeError("Unexpected error")):
            success, variables = plugins.execute_plugin(
                self.plugin_path, "aws", "us-east-1", "http://primary", "http://backup"
            )

        self.assertFalse(success)
        self.assertEqual(variables, {})

    def test_execute_plugin_forward_compatibility(self):
        """Test that plugins can be called with additional future arguments."""
        # Mock a successful plugin execution that ignores unknown arguments
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test_var=test_value\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            success, variables = plugins.execute_plugin(
                self.plugin_path, "aws", "us-east-1", "http://primary", "http://backup"
            )

        self.assertTrue(success)
        self.assertEqual(variables, {"test_var": "test_value"})

        # Verify the command was called with current arguments
        # (Future versions might add more arguments to this list)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        expected_args = [
            str(self.plugin_path),
            "--provider",
            "aws",
            "--region",
            "us-east-1",
            "--primary-url",
            "http://primary",
            "--backup-url",
            "http://backup",
        ]
        self.assertEqual(args, expected_args)

    def test_execute_plugin_with_additional_future_arguments(self):
        """Test plugin execution with hypothetical future arguments."""
        # This test simulates what might happen in a future version
        # that passes additional arguments to plugins

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "future_compatible=true\n"
        mock_result.stderr = ""

        # Create a modified version of execute_plugin that passes extra args
        def execute_plugin_future_version(
            plugin_path, provider, region, primary_url, backup_url, **kwargs
        ):
            """Hypothetical future version that passes additional arguments."""
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

            # Add hypothetical future arguments
            if kwargs.get("instance_type"):
                cmd.extend(["--instance-type", kwargs["instance_type"]])
            if kwargs.get("cloud_init_version"):
                cmd.extend(["--cloud-init-version", kwargs["cloud_init_version"]])

            # Simulate execution (in real test, plugin should handle unknown args gracefully)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=plugins.PLUGIN_TIMEOUT,
                cwd=tempfile.gettempdir(),
                env={"PATH": "/usr/bin:/bin"},
            )

            if result.returncode != 0:
                return False, {}  # pragma: no cover

            # Parse output (same logic as current version)
            variables = {}
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue  # pragma: no cover
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Basic validation
                    is_valid_name = (
                        key
                        and key.replace("_", "").replace("-", "").isalnum()
                        and key[0].isalpha()
                    )
                    if is_valid_name and key.lower() not in plugins.PROTECTED_VARIABLES:
                        variables[key] = value

            return True, variables

        with patch("subprocess.run", return_value=mock_result):
            # Test that future arguments don't break the system
            success, variables = execute_plugin_future_version(
                self.plugin_path,
                "aws",
                "us-east-1",
                "http://primary",
                "http://backup",
                instance_type="t3.micro",
                cloud_init_version="22.4",
            )

        self.assertTrue(success)
        self.assertEqual(variables, {"future_compatible": "true"})


class TestRunPlugins(unittest.TestCase):
    """Test the run_plugins function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("rlc.cloud_repos.plugins.discover_plugins")
    def test_run_plugins_no_plugins(self, mock_discover):
        """Test run_plugins when no plugins are found."""
        mock_discover.return_value = []

        result = plugins.run_plugins(
            "aws", "us-east-1", "http://primary", "http://backup"
        )

        self.assertEqual(result, {})

    @patch("rlc.cloud_repos.plugins.discover_plugins")
    @patch("rlc.cloud_repos.plugins.execute_plugin")
    def test_run_plugins_multiple_plugins(self, mock_execute, mock_discover):
        """Test run_plugins with multiple plugins."""
        plugin1 = Path("/test/plugin1.sh")
        plugin2 = Path("/test/plugin2.sh")
        mock_discover.return_value = [plugin1, plugin2]

        # First plugin succeeds, second fails
        mock_execute.side_effect = [
            (True, {"var1": "value1", "var2": "value2"}),
            (False, {}),
        ]

        result = plugins.run_plugins(
            "aws", "us-east-1", "http://primary", "http://backup"
        )

        # Should only get variables from successful plugin
        self.assertEqual(result, {"var1": "value1", "var2": "value2"})
        self.assertEqual(mock_execute.call_count, 2)

    @patch("rlc.cloud_repos.plugins.discover_plugins")
    @patch("rlc.cloud_repos.plugins.execute_plugin")
    def test_run_plugins_variable_override(self, mock_execute, mock_discover):
        """Test that later plugins can override earlier ones."""
        plugin1 = Path("/test/plugin1.sh")
        plugin2 = Path("/test/plugin2.sh")
        mock_discover.return_value = [plugin1, plugin2]

        mock_execute.side_effect = [
            (True, {"var1": "value1", "common": "first"}),
            (True, {"var2": "value2", "common": "second"}),
        ]

        result = plugins.run_plugins(
            "aws", "us-east-1", "http://primary", "http://backup"
        )

        # Later plugin should override the common variable
        self.assertEqual(
            result, {"var1": "value1", "var2": "value2", "common": "second"}
        )


class TestConfigurePlugins(unittest.TestCase):
    """Test the configure_plugins function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.basepath = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("rlc.cloud_repos.plugins.run_plugins")
    @patch("rlc.cloud_repos.plugins.write_dnf_var")
    def test_configure_plugins_success(self, mock_write_dnf_var, mock_run_plugins):
        """Test successful plugin configuration."""
        mock_run_plugins.return_value = {
            "custom_var": "custom_value",
            "repo_var": "repo_value",
        }

        plugins.configure_plugins(
            self.basepath, "aws", "us-east-1", "http://primary", "http://backup", True
        )

        # Should call run_plugins with correct arguments
        mock_run_plugins.assert_called_once_with(
            "aws", "us-east-1", "http://primary", "http://backup"
        )

        # Should write each variable
        self.assertEqual(mock_write_dnf_var.call_count, 2)
        mock_write_dnf_var.assert_any_call(
            self.basepath, "custom_var", "custom_value", True
        )
        mock_write_dnf_var.assert_any_call(
            self.basepath, "repo_var", "repo_value", True
        )

    @patch("rlc.cloud_repos.plugins.run_plugins")
    @patch("rlc.cloud_repos.plugins.write_dnf_var")
    def test_configure_plugins_no_variables(self, mock_write_dnf_var, mock_run_plugins):
        """Test plugin configuration with no variables returned."""
        mock_run_plugins.return_value = {}

        plugins.configure_plugins(
            self.basepath, "aws", "us-east-1", "http://primary", "http://backup", True
        )

        # Should call run_plugins but not write any variables
        mock_run_plugins.assert_called_once()
        mock_write_dnf_var.assert_not_called()
