import json
import os
from pathlib import Path

# Assuming pycodetags is installed or in your Python path
from pycodetags.__main__ import main as pycodetags_main
from pycodetags.config import CodeTagsConfig
from pycodetags.plugin_manager import reset_plugin_manager


# Helper to create a dummy pyproject.toml
def create_pyproject_toml(tmp_path: Path, config_content: str = "") -> Path:
    CodeTagsConfig._instance = None
    reset_plugin_manager()
    pyproject_path = tmp_path / "pyproject.toml"
    content = f"""
[tool.pycodetags]
{config_content}
"""
    pyproject_path.write_text(content)
    return pyproject_path


# Helper to create a dummy Python source file
def create_source_file(tmp_path: Path, file_name: str, content: str) -> Path:
    source_file_path = tmp_path / file_name
    source_file_path.write_text(content)
    return source_file_path


def test_end_to_end_report_text_format(tmp_path: Path, capsys):
    """
    Test end-to-end report generation for text format with mixed code tags.
    """
    CodeTagsConfig._instance = None

    # 1. Create a dummy pyproject.toml with basic configuration
    pyproject_toml_content = """
valid_authors = ["johndoe", "janesmith", "alice"]
valid_status = ["open", "closed"]
active_schemas = ["todo", "folk"]
"""
    create_pyproject_toml(tmp_path, pyproject_toml_content)

    # 2. Create a dummy Python source file with various code tags
    source_content = """
# This is a regular comment
def my_function():
    # TODO: Implement this feature <assignee:JohnDoe due:2025-12-31 priority:High category:Feature>
    pass

class MyClass:
    # FIXME(JaneSmith): Refactor this spaghetti code
    # This part needs to be cleaned up.
    def another_method(self):
        # BUG: Crashes when input is negative. <originator:Alice status:open tracker:https://example.com/bug/123>
        print("Hello")

# HACK: Temporarily disable validation for performance reasons
# This needs to be revisited after optimization.
"""
    source_file = create_source_file(tmp_path, "my_module.py", source_content)

    # 3. Simulate command-line arguments to generate a report
    # We pass the full path to the source file
    args = ["report", "--config", str(tmp_path / "pyproject.toml"), "--src", str(source_file), "--format", "text"]

    # Change current working directory to tmp_path for config discovery
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        exit_code = pycodetags_main(args)
    finally:
        os.chdir(original_cwd)

    # 4. Assert the exit code
    assert exit_code == 0, f"CLI exited with non-zero code: {exit_code}"

    # 5. Assert that parts of the expected output are present
    output = capsys.readouterr().out

    with capsys.disabled():
        print("\n--- Captured Output (Text Format) ---")
        print(output)
        print("------------------------------------")

    # Assert for PEP350 TODO
    assert "--- TODO ---" in output
    # Johndoe is lowered! and 1st letter uppered! Not good!
    assert "Implement this feature\n# <JohnDoe due:2025-12-31 priority:High category:Feature>" in output

    # Assert for PEP350 BUG
    assert "--- BUG ---" in output
    assert (
        'Crashes when input is negative.\n# <originator:Alice tracker:"https://example.com/bug/123" status:open>'
        in output
    )

    # Assert for Folk FIXME (should have JaneSmith as assignee due to default_field_meaning)
    # The folk tag is converted to a TODO object and then printed in PEP350-like format.
    assert "--- FIXME ---" in output
    # Folk tags do not extract 'default_field' as a separate field in the final TODO object unless promoted
    # to an explicit field like 'assignee'. The comment content for folk tags will include the original
    # (JaneSmith) if it was part of the comment, but the structured 'assignee' field will be populated.
    assert "Refactor this spaghetti code <JaneSmith>" in output

    # Assert for Folk HACK
    assert "--- HACK ---" in output
    assert "Temporarily disable validation for performance reasons" in output


def test_end_to_end_report_json_format(tmp_path: Path, capsys):
    """
    Test end-to-end report generation for JSON format.
    """
    CodeTagsConfig._instance = None
    create_pyproject_toml(tmp_path)  # Default config is fine for this test

    source_content = """
def another_func():
    # IDEA: Create a new report type <assignee:Alice due:2026-01-15>
    pass
"""
    source_file = create_source_file(tmp_path, "another_module.py", source_content)

    args = ["report", "--config", str(tmp_path / "pyproject.toml"), "--src", str(source_file), "--format", "json"]

    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        exit_code = pycodetags_main(args)
    finally:
        os.chdir(original_cwd)

    assert exit_code == 0
    output = capsys.readouterr().out

    with capsys.disabled():
        print("\n--- Captured Output (JSON Format) ---")
        print(output)
        print("------------------------------------")

    data = json.loads(output)

    assert "todos" in data
    assert len(data["todos"]) >= 1  # May include other defaults
    found_idea = False
    for todo in data["todos"]:
        if todo.get("code_tag") == "IDEA":
            assert todo.get("comment") == "Create a new report type"
            assert todo.get("assignee") in ("Alice", ["Alice"])
            assert todo.get("due") == "2026-01-15"
            found_idea = True
            break
    assert found_idea, "IDEA tag not found in JSON output"

    assert "exceptions" in data
    # No exceptions expected in this specific source content
    assert len(data["exceptions"]) == 0


def test_end_to_end_validation_report(tmp_path: Path, capsys):
    """
    Test end-to-end validation report generation.
    """
    CodeTagsConfig._instance = None

    # Config with mandatory fields and valid authors
    pyproject_toml_content = """
valid_authors = ["johndoe"]
mandatory_fields = ["originator", "due"]
active_schemas = ["todo", "folk"]
"""
    create_pyproject_toml(tmp_path, pyproject_toml_content)

    source_content = """
# TODO: This task is missing mandatory fields.

# TODO: Valid task. <originator:JohnDoe due:2025-07-01>

# DONE: This is a completed task. <assignee:JohnDoe closed_date:2025-06-27>
"""
    source_file = create_source_file(tmp_path, "validation_module.py", source_content)

    args = ["report", "--config", str(tmp_path / "pyproject.toml"), "--src", str(source_file), "--validate"]

    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        exit_code = pycodetags_main(args)
    finally:
        os.chdir(original_cwd)

    assert exit_code == 0
    output = capsys.readouterr().out
    with capsys.disabled():
        print("\n--- Captured Output (Validation) ---")
        print(output)
        print("------------------------------------")

    # Assert for validation errors
    assert "TODO: This task is missing mandatory fields." in output
    assert "originator is required" in output
    assert "due is required" in output

    # Assert for no errors on valid task
    assert "TODO: Valid task." not in output

    # Assert for done task validation
    assert "DONE: This is a completed task." in output
    # A "DONE" tag implicitly means it's closed, so it requires an assignee, release, and closed_date
    assert "Item is done, missing release" in output
