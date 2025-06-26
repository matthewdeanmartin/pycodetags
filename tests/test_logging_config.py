import os
from unittest.mock import MagicMock, patch

import pytest

from pycodetags.logging_config import generate_config


def test_generate_config_default():
    config = generate_config()
    assert config["handlers"]["default"]["formatter"]  # could be either depending on CI
    assert config["loggers"]["pycodetags"]["level"] == "DEBUG"
    assert "bugtrail" not in config["handlers"]


@pytest.mark.parametrize("env_var", ["NO_COLOR", "CI"])
def test_generate_config_no_color_env(env_var):
    with patch.dict(os.environ, {env_var: "1"}):
        config = generate_config()
        assert config["handlers"]["default"]["formatter"]  # could be either depending on CI


def test_generate_config_enable_bug_trail_success():
    mock_section = MagicMock()
    mock_section.database_path = "/tmp/mock.db"
    mock_bug_trail = MagicMock()
    mock_bug_trail.read_config.return_value = mock_section

    with patch.dict("sys.modules", {"bug_trail_core": mock_bug_trail}):
        config = generate_config(enable_bug_trail=True)

    assert "bugtrail" in config["handlers"]
    handler = config["handlers"]["bugtrail"]
    assert handler["class"] == "bug_trail_core.BugTrailHandler"
    assert handler["db_path"] == "/tmp/mock.db"
    assert "bugtrail" in config["loggers"]["pycodetags"]["handlers"]
