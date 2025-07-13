import os

import pytest

# To test the script, we need to import its functions.
# Assuming the script is named `pycodetags_init.py` and is in the same directory.
# If it's part of a package, you'd import it differently.
from pycodetags.app_config.config_init import (
    _find_potential_src_folders,
    _write_to_pyproject_safe,
    init_pycodetags_config,
)

# --- Fixtures ---


@pytest.fixture
def temp_project_dir(tmp_path):
    """
    Creates a temporary directory for each test and changes the CWD into it.
    This provides a clean slate for file system operations.
    """
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    # Create a dummy project structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").touch()
    (tmp_path / "my_app").mkdir()
    (tmp_path / "my_app" / "app.py").touch()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_code.py").touch()
    (tmp_path / ".venv").mkdir()
    yield tmp_path
    os.chdir(original_cwd)


# --- Test Cases ---


def test_init_config_when_already_exists(temp_project_dir, capsys):
    """
    Test that the script exits gracefully if config already exists.
    """
    # Arrange: Create a pyproject.toml with the section already present.
    pyproject_content = """
[tool.other_tool]
name = "some_tool"

[tool.pycodetags]
src = ["src"]
"""
    with open("pyproject.toml", "w", encoding="utf-8") as f:
        f.write(pyproject_content)

    # Act: Run the initializer
    init_pycodetags_config()

    # Assert: Check that the "already exists" message is printed and file is unchanged.
    captured = capsys.readouterr()
    assert "already exists" in captured.out

    with open("pyproject.toml", encoding="utf-8") as f:
        final_content = f.read()
    assert final_content == pyproject_content


def test_init_config_with_auto_detect_selection(temp_project_dir, monkeypatch, capsys):
    """
    Test the full flow where a user selects an auto-detected folder.
    """
    # Arrange: Mock user input to select the first option ('src').
    # The detected folders should be 'src' and 'my_app'.
    monkeypatch.setattr("builtins.input", lambda _: "1")

    # Act: Run the initializer
    init_pycodetags_config()

    # Assert: Check that pyproject.toml was created and has the correct content.
    assert os.path.exists("pyproject.toml")
    with open("pyproject.toml", encoding="utf-8") as f:
        content = f.read()

    assert "[tool.pycodetags]" in content
    assert 'src = ["src"]' in content
    captured = capsys.readouterr()
    assert "Using 'src' as the primary source folder." in captured.out


def test_init_config_with_cancel_option(temp_project_dir, monkeypatch, capsys):
    """
    Test that the script aborts if the user selects 'Cancel'.
    """
    # Arrange: Mock user input to select "Cancel".
    # Detected folders are 'src', 'my_app', 'tests'. Manual is 4, Cancel is 5.
    monkeypatch.setattr("builtins.input", lambda _: "5")

    # Act: Run the initializer
    init_pycodetags_config()

    # Assert: Check that no file was created and an abort message was printed.
    assert not os.path.exists("pyproject.toml")
    captured = capsys.readouterr()
    assert "No source folder selected. Aborting initialization." in captured.out


def test_find_potential_src_folders(temp_project_dir):
    """
    Test the folder detection logic directly.
    """
    # Act: Run the detection function.
    folders = _find_potential_src_folders()

    expected_folders = ["src", "my_app", "tests"]

    # We check with sets to ignore order.
    assert set(folders) == set(expected_folders)


def test_write_to_existing_pyproject_safe(temp_project_dir):
    """
    Test that the write function correctly appends to an existing file.
    """
    # Arrange: Create a pyproject.toml with some pre-existing content.
    initial_content = "[tool.poetry]\nname = 'my-package'"
    with open("pyproject.toml", "w", encoding="utf-8") as f:
        f.write(initial_content)

    new_section = "[tool.pycodetags]\nsrc = ['src']"

    # Act
    _write_to_pyproject_safe(new_section, "pyproject.toml")

    # Assert
    with open("pyproject.toml", encoding="utf-8") as f:
        final_content = f.read()

    expected_content = initial_content + "\n\n" + new_section
    assert final_content.replace(" ", "").replace("\n", "") == expected_content.replace(" ", "").replace("\n", "")
