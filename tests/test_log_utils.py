from unittest.mock import patch

from rlc.cloud_repos import log_utils


def test_logging_setup():
    with patch("rlc.cloud_repos.log_utils.logger.hasHandlers", return_value=False):
        log_utils.setup_logging(debug=False)

        # Check if the logger has handlers
        assert len(log_utils.logger.handlers) == 2
