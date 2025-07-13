# from pathlib import Path
# from unittest.mock import patch
#
# import pytest
#
# from pycodetags.config import CodeTagsConfig
#
#
# @pytest.fixture
# def pyproject_file(tmp_path: Path) -> Path:
#     content = """
# [tool.pycodetags]
# valid_authors = ["Alice", "Bob"]
# valid_authors_schema = "single_column"
# valid_status = ["done", "closed"]
# user_identification_technique = "os"
# user_env_var = "MY_USER"
# tracker_style = "url"
# valid_priorities = ["high", "medium", "low"]
# valid_iterations = ["1", "2"]
# mandatory_fields = ["originator", "origination_date"]
# enable_actions = true
# default_action = "warn"
# action_on_past_due = true
# action_only_on_responsible_user = true
# disable_on_ci = false
# use_dot_env = true
# releases_schema = "semantic"
# """
#     path = tmp_path / "pyproject.toml"
#     path.write_text(content, encoding="utf-8")
#     return path
#
#
# def test_valid_authors_from_config(pyproject_file):
#     config = CodeTagsConfig(str(pyproject_file))
#     assert config.valid_authors() == ["alice", "bob"]
#
#
# def test_valid_status_lowercased(pyproject_file):
#     config = CodeTagsConfig(str(pyproject_file))
#     assert config.valid_status() == ["done", "closed"]
#
#
# def test_valid_priorities(pyproject_file):
#     config = CodeTagsConfig(str(pyproject_file))
#     assert config.valid_priorities() == ["high", "medium", "low"]
#
#
# def test_tracker_style_valid(pyproject_file):
#     config = CodeTagsConfig(str(pyproject_file))
#     assert config.tracker_style() == "url"
#
#
# def test_invalid_tracker_style_raises(tmp_path):
#     bad_config = """
# [tool.pycodetags]
# tracker_style = "invalid_style"
# """
#     f = tmp_path / "pyproject.toml"
#     f.write_text(bad_config, encoding="utf-8")
#     config = CodeTagsConfig(str(f))
#     with pytest.raises(Exception, match="Invalid configuration: tracker_style must be in"):
#         config.tracker_style()
#
#
# def test_valid_authors_from_file(tmp_path):
#     authors_file = tmp_path / "AUTHORS.md"
#     authors_file.write_text("Alice\nBob\n", encoding="utf-8")
#
#     file_name = str(authors_file).replace("\\", "/")
#     config_text = f"""
# [tool.pycodetags]
# valid_authors_file = "{file_name}"
# valid_authors_schema = "single_column"
# """
#     pyproject = tmp_path / "pyproject.toml"
#     pyproject.write_text(config_text, encoding="utf-8")
#
#     config = CodeTagsConfig(str(pyproject))
#     assert config.valid_authors() == ["Alice\n", "Bob\n"]  # Note: newline remains!
#
#
# def test_missing_valid_authors_schema_raises(tmp_path):
#     authors_file = tmp_path / "AUTHORS.md"
#     authors_file.write_text("Alice\n", encoding="utf-8")
#
#     file_name = str(authors_file).replace("\\", "/")
#     # escaped backslashes e.g. \ are interpreted as hex in toml!
#     config_text = f"""
# [tool.pycodetags]
# valid_authors_file = "{file_name}"
# """
#     pyproject = tmp_path / "pyproject.toml"
#     pyproject.write_text(config_text, encoding="utf-8")
#
#     config = CodeTagsConfig(str(pyproject))
#     with pytest.raises(Exception, match="must be valid_authors_schema must be set"):
#         config.valid_authors_schema()
#
#
# def test_current_user_override(pyproject_file):
#     config = CodeTagsConfig(str(pyproject_file), set_user="Charlie")
#     assert config.current_user() == "Charlie"
#
#
# @patch("pycodetags.config.get_current_user")
# def test_current_user_from_os(mock_get_user, pyproject_file):
#     mock_get_user.return_value = "Dana"
#     config = CodeTagsConfig(str(pyproject_file))
#     assert config.current_user() == "Dana"
#     mock_get_user.assert_called_once()
#
#
# def test_singleton_get_set_instance(pyproject_file):
#     CodeTagsConfig.set_instance(None)
#     instance = CodeTagsConfig.get_instance(str(pyproject_file))
#     assert isinstance(instance, CodeTagsConfig)
#
#     CodeTagsConfig.set_instance(None)
#     new_instance = CodeTagsConfig.get_instance(str(pyproject_file))
#     assert new_instance is not None
