from pathlib import Path

import pytest

from pycodetags.config import CodeTagsConfig


@pytest.fixture
def pyproject_file(tmp_path: Path) -> Path:
    content = """
[tool.pycodetags]
valid_authors = ["Alice", "Bob"]
valid_authors_schema = "single_column"
valid_status = ["done", "closed"]
user_identification_technique = "os"
user_env_var = "MY_USER"
tracker_style = "url"
valid_priorities = ["high", "medium", "low"]
valid_iterations = ["1", "2"]
mandatory_fields = ["originator", "origination_date"]
enable_actions = true
default_action = "warn"
action_on_past_due = true
action_only_on_responsible_user = true
disable_on_ci = false
use_dot_env = true
releases_schema = "semantic"
"""
    path = tmp_path / "pyproject.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_singleton_get_set_instance(pyproject_file):
    CodeTagsConfig.set_instance(None)
    instance = CodeTagsConfig.get_instance(str(pyproject_file))
    assert isinstance(instance, CodeTagsConfig)

    CodeTagsConfig.set_instance(None)
    new_instance = CodeTagsConfig.get_instance(str(pyproject_file))
    assert new_instance is not None
