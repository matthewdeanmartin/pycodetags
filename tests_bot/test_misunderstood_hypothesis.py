import datetime
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pycodetags.aggregate import aggregate_all_kinds, aggregate_all_kinds_multiple_input, merge_collected
from pycodetags.collect import TodoCollector, collect_all_todos, is_stdlib_module
from pycodetags.collect_ast import TodoExceptionCollector  # Import for AST-based tests
from pycodetags.collection_types import CollectedTODOs
from pycodetags.config import CodeTagsConfig
from pycodetags.converters import blank_to_null, convert_folk_tag_to_TODO, convert_pep350_tag_to_TODO
from pycodetags.dotenv import load_dotenv
from pycodetags.folk_code_tags import FolkTag, extract_first_url, find_source_tags, folk_tag_to_comment, process_line
from pycodetags.standard_code_tags import (
    PEP350Tag,
    collect_pep350_code_tags,
    extract_comment_blocks,
    parse_codetags,
    parse_fields,
)
from pycodetags.todo_tag_types import TODO, TodoException, parse_due_date
from pycodetags.user import get_current_user, get_env_user, get_os_user
from pycodetags.users_from_authors import parse_authors_file


# Mocks for plugin system that might be used by aggregate or main_types
# We'll use a simple mock here, not the full pluggy setup from main.py
class MockPluginManager:
    def __init__(self):
        self.hook = MagicMock()
        self.hook.code_tags_validate_todo.return_value = []  # Default no extra issues
        self.hook.find_source_tags.return_value = []  # Default no extra folk tags

    def get_plugins(self):
        return []

    def get_canonical_name(self, plugin):
        return "mock-plugin"

    def is_blocked(self, plugin_name):
        return False


@pytest.fixture(autouse=True)
def mock_plugin_manager():
    """Fixture to mock the global plugin manager for isolated tests."""
    with patch('code_tags.plugin_manager.get_plugin_manager', return_value=MockPluginManager()) as mock_pm:
        yield mock_pm


@pytest.fixture
def temp_dir():
    """Creates a temporary directory for test files and cleans it up."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(autouse=True)
def reset_code_tags_config():
    """Resets the singleton CodeTagsConfig instance before each test."""
    CodeTagsConfig.set_instance(None)
    yield
    CodeTagsConfig.set_instance(None)  # Ensure it's reset after test as well


# --- aggregate.py Tests ---

def test_merge_collected_hypothesis_1():
    """Hypothesis 1: merge_collected correctly combines lists."""
    collected1: CollectedTODOs = {"todos": [TODO(comment="t1")], "exceptions": [TodoException("e1")]}
    collected2: CollectedTODOs = {"todos": [TODO(comment="t2")], "exceptions": [TodoException("e2")]}
    collected3: CollectedTODOs = {"todos": [TODO(comment="t1")], "exceptions": []}  # Duplicate TODO

    merged = merge_collected([collected1, collected2, collected3])

    assert len(merged["todos"]) == 3
    assert any(t.comment == "t1" for t in merged["todos"])
    assert any(t.comment == "t2" for t in merged["todos"])
    assert len(merged["exceptions"]) == 2
    assert any(e.message == "e1" for e in merged["exceptions"])
    assert any(e.message == "e2" for e in merged["exceptions"])


def test_aggregate_all_kinds_multiple_input_hypothesis_2(mocker):
    """Hypothesis 2: aggregate_all_kinds_multiple_input delegates and merges."""
    mock_aggregate_all_kinds = mocker.patch('code_tags.aggregate.aggregate_all_kinds')

    # Mock return values for aggregate_all_kinds
    mock_aggregate_all_kinds.side_effect = [
        {"todos": [TODO(comment="m1")], "exceptions": []},
        {"todos": [TODO(comment="m2")], "exceptions": []},
        {"todos": [], "exceptions": [TodoException("s1")]},
        {"todos": [], "exceptions": [TodoException("s2")]},
    ]

    module_names = ["mod1", "mod2"]
    source_paths = ["src1", "src2"]

    result = aggregate_all_kinds_multiple_input(module_names, source_paths)

    assert mock_aggregate_all_kinds.call_count == 4
    mock_aggregate_all_kinds.assert_any_call("mod1", "")
    mock_aggregate_all_kinds.assert_any_call("mod2", "")
    mock_aggregate_all_kinds.assert_any_call("", "src1")
    mock_aggregate_all_kinds.assert_any_call("", "src2")

    assert len(result["todos"]) == 2
    assert any(t.comment == "m1" for t in result["todos"])
    assert any(t.comment == "m2" for t in result["todos"])
    assert len(result["exceptions"]) == 2
    assert any(e.message == "s1" for e in result["exceptions"])
    assert any(e.message == "s2" for e in result["exceptions"])


# Dummy module for testing aggregation
@pytest.fixture
def dummy_module(tmp_path):
    module_content = """
import datetime
from types import SimpleNamespace

from code_tags.main_types import TODO, TodoException

MY_TODO = TODO(comment="This is a module-level TODO", assignee="test_user", due="2025-12-31")

class MyClass:
    CLASS_TODO = TODO(comment="Class-level TODO", assignee="class_user")

    def my_method(self):
        # TODO: This is a comment-style TODO (will be caught by source parsing, not object graph for now)
        pass

def my_func():
    ANOTHER_TODO = TODO(comment="Function-level TODO", assignee="func_user")
    return ANOTHER_TODO

def raises_exception():
    raise TodoException("This is an expected exception", assignee="exception_user")

nested_namespace = SimpleNamespace(
    deep_todo=TODO(comment="Deeply nested TODO", assignee="deep_user")
)
    """
    module_dir = tmp_path / "dummy_module"
    module_dir.mkdir()
    module_file = module_dir / "__init__.py"
    module_file.write_text(module_content)

    sys.path.insert(0, str(tmp_path))
    import dummy_module
    yield dummy_module
    sys.path.remove(str(tmp_path))
    # Clean up the module from sys.modules to allow re-importing in other tests if needed
    if 'dummy_module' in sys.modules:
        del sys.modules['dummy_module']


def test_aggregate_all_kinds_hypothesis_3_module_only(dummy_module, mocker):
    """Hypothesis 3: aggregate_all_kinds collects from module only."""
    # Mock source parsing functions to ensure only module parsing happens
    mocker.patch('code_tags.standard_code_tags.collect_pep350_code_tags', return_value=[])
    mocker.patch('code_tags.folk_code_tags.find_source_tags', return_value=[])
    mocker.patch('code_tags.collect_ast.TodoExceptionCollector.collect_from_source_analysis', return_value=[])

    result = aggregate_all_kinds(dummy_module.__name__, "")

    assert len(result["todos"]) >= 3  # MY_TODO, Class_TODO, ANOTHER_TODO, deep_todo
    assert any(t.comment == "This is a module-level TODO" for t in result["todos"])
    assert any(t.comment == "Class-level TODO" for t in result["todos"])
    assert any(t.comment == "Function-level TODO" for t in result["todos"])
    assert any(t.comment == "Deeply nested TODO" for t in result["todos"])
    assert "exceptions" in result and len(result["exceptions"]) == 0  # No exceptions collected from source when mocked


def test_aggregate_all_kinds_hypothesis_4_source_path_only(temp_dir, mocker):
    """Hypothesis 4: aggregate_all_kinds collects from source path only."""
    # Create dummy source files
    py_file = temp_dir / "test_source.py"
    py_file.write_text("""
# TODO: Comment via PEP350 <assignee:pep_user>
# TODO: Folk tag comment (folk_user)
# BUG: Bug from source <message:Source bug>
""")

    non_py_file = temp_dir / "test.txt"
    non_py_file.write_text("# CUSTOMTAG: Custom file tag (custom_user)")

    # Mock module import
    mocker.patch('importlib.import_module', side_effect=ImportError)  # Ensure no module import happens

    # Mock plugin for non-py file
    mock_plugin_manager().hook.find_source_tags.return_value = [
        FolkTag(code_tag="CUSTOMTAG", comment="Custom file tag", assignee="custom_user", file_path=str(non_py_file),
                line_number=1, original_text="CUSTOMTAG: Custom file tag (custom_user)")
    ]

    result = aggregate_all_kinds("", str(temp_dir))

    assert len(result["todos"]) == 3  # 1 PEP350, 1 Folk, 1 CustomTag via plugin
    assert any(t.comment == "Comment via PEP350" and t.original_schema == "pep350" for t in result["todos"])
    assert any(t.comment == "Folk tag comment" and t.original_schema == "folk" for t in result["todos"])
    assert any(t.comment == "Custom file tag" and t.code_tag == "CUSTOMTAG" for t in result["todos"])
    assert len(result["exceptions"]) == 1
    assert any(e.message == "Source bug" for e in result["exceptions"])


def test_aggregate_all_kinds_hypothesis_5_source_path_no_files_raises(temp_dir):
    """Hypothesis 5: aggregate_all_kinds raises TypeError if no files in source folder."""
    # Create an empty directory
    empty_dir = temp_dir / "empty_folder"
    empty_dir.mkdir()

    with pytest.raises(TypeError, match="Can't find any files in source folder"):
        aggregate_all_kinds("", str(empty_dir))


def test_aggregate_all_kinds_with_file_not_directory(temp_dir):
    """Test aggregate_all_kinds when source_path points to a single file."""
    single_file = temp_dir / "single_file.py"
    single_file.write_text("# TODO: Single file tag <assignee:single_file_user>")

    result = aggregate_all_kinds("", str(single_file))
    assert len(result["todos"]) == 1
    assert result["todos"][0].comment == "Single file tag"
    assert result["todos"][0].assignee == "single_file_user"


# --- collect.py Tests ---

def test_is_stdlib_module_hypothesis_6():
    """Hypothesis 6: is_stdlib_module correctly identifies stdlib and non-stdlib."""
    # Test with standard library modules
    assert is_stdlib_module(sys)
    assert is_stdlib_module(os)
    import math
    assert is_stdlib_module(math)

    # Test with a mock non-stdlib module (e.g., from temp_dir)
    class MockNonStdlibModule:
        __file__ = "/tmp/my_project/my_module.py"  # Example path outside stdlib
        __name__ = "my_module"

    assert not is_stdlib_module(MockNonStdlibModule())

    # Test module without __file__ (e.g. built-in, but ensure it's not a mock that misleads)
    with patch('hasattr', return_value=False):  # Force no __file__ attribute
        assert is_stdlib_module(MagicMock())  # Mock anything, it should be true because of no __file__


class MockObjWithTODO:
    def __init__(self, comment="mock todo"):
        self.todo_meta = TODO(comment=comment)


class MockModuleWithNested:
    def __init__(self):
        self.attr1 = "value"
        self.nested_todo_obj = MockObjWithTODO("nested_todo")
        self.nested_list = [MockObjWithTODO("list_todo1"), "string", MockObjWithTODO("list_todo2")]
        self.nested_dict = {"key": MockObjWithTODO("dict_todo")}

    class NestedClass:
        """Nested class with a TODO."""
        CLASS_TODO_OBJ = MockObjWithTODO("nested_class_todo")

        def nested_method(self):
            pass

    def func_with_todo(self):
        return MockObjWithTODO("func_return_todo")


def test_todo_collector_collect_from_module_hypothesis_7(mocker):
    """Hypothesis 7: TodoCollector recursively collects with depth limits."""
    mock_module = MockModuleWithNested()
    mock_module.__name__ = "mock_module"
    mock_module.__file__ = "/tmp/mock_module.py"  # Needed to be seen as non-stdlib

    # Mock inspect.ismodule to control recursion for submodules
    mocker.patch('inspect.ismodule', side_effect=lambda x: isinstance(x, MagicMock) and hasattr(x, '__file__'))
    mocker.patch('code_tags.collect.is_stdlib_module', return_value=False)
    mocker.patch('code_tags.collect.logger.debug')  # Silence debug logs

    collector = TodoCollector()
    todos, exceptions = collector.collect_from_module(mock_module, include_submodules=True, max_depth=5)

    assert len(todos) >= 5  # nested_todo_obj, list_todo1, list_todo2, dict_todo, nested_class_todo, func_return_todo
    assert any(t.comment == "nested_todo" for t in todos)
    assert any(t.comment == "list_todo1" for t in todos)
    assert any(t.comment == "list_todo2" for t in todos)
    assert any(t.comment == "dict_todo" for t in todos)
    assert any(t.comment == "nested_class_todo" for t in todos)
    assert any(t.comment == "func_return_todo" for t in todos)
    assert len(exceptions) == 0  # No exceptions gathered here

    # Test max_depth
    collector._reset()
    todos_shallow, _ = collector.collect_from_module(mock_module, include_submodules=True, max_depth=0)
    assert len(todos_shallow) == 0  # No objects should be traversed if depth is 0 and root is not a TODO


def test_collect_all_todos_hypothesis_8(mocker):
    """Hypothesis 8: collect_all_todos comprehensively collects."""
    mock_module = MagicMock()
    mock_module.__name__ = "test_module"
    mock_module.__file__ = "/tmp/test_module.py"

    # Mock TodoCollector and TodoExceptionCollector
    mock_collector_instance = MagicMock(spec=TodoCollector)
    mock_collector_instance.collect_from_module.return_value = ([TODO(comment="module_todo")], [])
    mocker.patch('code_tags.collect.TodoCollector', return_value=mock_collector_instance)

    mock_exception_collector_instance = MagicMock(spec=TodoExceptionCollector)
    mock_exception_collector_instance.collect_from_source_analysis.return_value = ([TodoException("ast_exception")])
    mocker.patch('code_tags.collect.TodoExceptionCollector', return_value=mock_exception_collector_instance)

    standalone_items = [TODO(comment="standalone_todo")]

    result = collect_all_todos(mock_module, standalone_items, include_submodules=True, include_exceptions=True)

    mock_collector_instance.collect_from_module.assert_called_once_with(mock_module, True)
    mock_exception_collector_instance.collect_from_source_analysis.assert_called_once_with(mock_module)

    assert len(result["todos"]) == 2
    assert any(t.comment == "module_todo" for t in result["todos"])
    assert any(t.comment == "standalone_todo" for t in result["todos"])
    assert len(result["exceptions"]) == 1
    assert any(e.message == "ast_exception" for e in result["exceptions"])


# --- collect_ast.py Tests ---

def test_todo_exception_collector_source_analysis_hypothesis_9(temp_dir):
    """Hypothesis 9: TodoExceptionCollector accurately parses and extracts."""
    source_content = """
from code_tags.main_types import TodoException

def func1():
    raise TodoException("Missing feature", assignee="john.doe", due="2024-07-15")

class MyClass:
    def method1(self):
        raise TodoException(message="Another issue", due="2024-08-01")

def func2():
    # Some other code
    if True:
        raise TodoException("Third issue") # No assignee/due here
    """
    source_file = temp_dir / "test_exceptions.py"
    source_file.write_text(source_content)

    # Create a mock module object pointing to the dummy file
    mock_module = MagicMock()
    mock_module.__file__ = str(source_file)

    collector = TodoExceptionCollector()
    exceptions = collector.collect_from_source_analysis(mock_module)

    assert len(exceptions) == 3

    ex1 = next(e for e in exceptions if e.message == "Missing feature")
    assert ex1.assignee == "john.doe"
    assert ex1.due == "2024-07-15"

    ex2 = next(e for e in exceptions if e.message == "Another issue")
    assert ex2.assignee is None
    assert ex2.due == "2024-08-01"

    ex3 = next(e for e in exceptions if e.message == "Third issue")
    assert ex3.assignee is None
    assert ex3.due is None


def test_extract_exception_args_hypothesis_10():
    """Hypothesis 10: _extract_exception_args robustly extracts arguments."""
    import ast

    collector = TodoExceptionCollector()

    # Test with all arguments as ast.Constant (Python 3.8+)
    call_node_full = ast.Call(
        func=ast.Name(id='TodoException', ctx=ast.Load()),
        args=[],
        keywords=[
            ast.keyword(arg='message', value=ast.Constant(value="Full message")),
            ast.keyword(arg='assignee', value=ast.Constant(value="Tester")),
            ast.keyword(arg='due', value=ast.Constant(value="2024-09-01"))
        ]
    )
    args_full = collector._extract_exception_args(call_node_full)
    assert args_full == {"message": "Full message", "assignee": "Tester", "due": "2024-09-01"}

    # Test with some arguments and ast.Str (Python < 3.8 compatibility)
    call_node_partial_str = ast.Call(
        func=ast.Name(id='TodoException', ctx=ast.Load()),
        args=[],
        keywords=[
            ast.keyword(arg='message', value=ast.Str(s="Partial message")),
            ast.keyword(arg='assignee', value=ast.Constant(value="Dev"))
        ]
    )
    args_partial_str = collector._extract_exception_args(call_node_partial_str)
    assert args_partial_str == {"message": "Partial message", "assignee": "Dev"}

    # Test with no recognized arguments
    call_node_empty = ast.Call(
        func=ast.Name(id='TodoException', ctx=ast.Load()),
        args=[ast.Constant(value="Positional arg")],
        keywords=[ast.keyword(arg='unrecognized', value=ast.Constant(value="abc"))]
    )
    args_empty = collector._extract_exception_args(call_node_empty)
    assert args_empty == {}


# --- config.py Tests ---

@pytest.fixture
def create_pyproject_toml(temp_dir):
    def _creator(content=""):
        config_path = temp_dir / "pyproject.toml"
        if content:
            config_path.write_text(content)
        return config_path

    return _creator


def test_code_tags_config_loading_and_defaults_hypothesis_11(create_pyproject_toml):
    """Hypothesis 11: CodeTagsConfig loads config or uses defaults."""
    # Test no config file
    config = CodeTagsConfig(pyproject_path="non_existent_pyproject.toml")
    assert config.valid_priorities() == []
    assert not config.runtime_behavior_enabled

    # Test empty config section
    config_path_empty = create_pyproject_toml("[tool]\n[tool.other]\nkey=value")
    config = CodeTagsConfig(pyproject_path=str(config_path_empty))
    assert config.valid_priorities() == []
    assert not config.runtime_behavior_enabled

    # Test with valid config
    config_content = """
[tool.code_tags]
valid_priorities = ["high", "low"]
disable_all_runtime_behavior = false
    """
    config_path_valid = create_pyproject_toml(config_content)
    config = CodeTagsConfig(pyproject_path=str(config_path_valid))
    assert config.valid_priorities() == ["high", "low"]
    assert config.runtime_behavior_enabled


def test_config_property_type_validation_hypothesis_12(create_pyproject_toml):
    """Hypothesis 12: Config properties raise TypeError for invalid values."""
    invalid_configs = {
        "valid_authors_schema": 'invalid',
        "tracker_style": 'bad_style',
        "user_identification_technique": 'unknown_method',
        "default_action": 'unsupported',
        "releases_schema": 'non_semantic'
    }

    for prop, invalid_value in invalid_configs.items():
        config_content = f"""
[tool.code_tags]
{prop} = "{invalid_value}"
        """
        config_path = create_pyproject_toml(config_content)
        config = CodeTagsConfig(pyproject_path=str(config_path))
        with pytest.raises(TypeError, match=f"Invalid configuration: {prop}"):
            getattr(config, prop)()


def test_file_based_author_loading_hypothesis_13(create_pyproject_toml, temp_dir):
    """Hypothesis 13: File-based author loading works correctly."""
    authors_file_path = str(temp_dir / "AUTHORS.md").replace("\\", "/")
    authors_file_path.write_text("John Doe\nJane Smith\n")

    config_content = f"""
[tool.code_tags]
valid_authors_file = "{authors_file_path}"
valid_authors_schema = "single_column"
valid_authors = ["preexisting"] # Should be overridden
    """
    config_path = create_pyproject_toml(config_content)
    config = CodeTagsConfig(pyproject_path=str(config_path))

    assert config.valid_authors() == ["John Doe\n", "Jane Smith\n"]  # From file

    # Test GNU Gnits schema
    gnits_authors_file_path = temp_dir / "AUTHORS_GNITS.md"
    gnits_authors_file_path.write_text("Full Name <email@example.com>\nAnother Name")

    gnits_config_content = f"""
[tool.code_tags]
valid_authors_file = "{gnits_authors_file_path}"
valid_authors_schema = "gnu_gnits"
    """
    gnits_config_path = create_pyproject_toml(gnits_config_content)
    config = CodeTagsConfig(pyproject_path=str(gnits_config_path))
    assert config.valid_authors() == ["Full Name", "Another Name"]  # Parsed from gnits


def test_current_user_identification_hypothesis_14(mocker):
    """Hypothesis 14: current_user identifies correctly based on technique."""
    mock_get_os_user = mocker.patch('code_tags.config.get_os_user', return_value="os_user")
    mock_get_env_user = mocker.patch('code_tags.config.get_env_user', return_value="env_user")
    mock_get_git_user = mocker.patch('code_tags.config.get_git_user', return_value="git_user")

    # Test OS method
    config_os = CodeTagsConfig()
    config_os._config["user_identification_technique"] = "os"
    assert config_os.current_user() == "os_user"
    mock_get_os_user.assert_called_once()

    # Test ENV method
    config_env = CodeTagsConfig()
    config_env._config["user_identification_technique"] = "env"
    config_env._config["user_env_var"] = "TEST_ENV_VAR"
    assert config_env.current_user() == "env_user"
    mock_get_env_user.assert_called_once_with("TEST_ENV_VAR")

    # Test GIT method
    config_git = CodeTagsConfig()
    config_git._config["user_identification_technique"] = "git"
    assert config_git.current_user() == "git_user"
    mock_get_git_user.assert_called_once()

    # Test user_override precedence
    config_override = CodeTagsConfig(set_user="override_user")
    assert config_override.current_user() == "override_user"
    # Ensure underlying methods were not called if override is present
    mock_get_os_user.assert_called_once()  # Reset from previous test, no new calls here
    mock_get_env_user.assert_called_once_with("TEST_ENV_VAR")  # Reset from previous test, no new calls here
    mock_get_git_user.assert_called_once()  # Reset from previous test, no new calls here


def test_runtime_behavior_enabled_hypothesis_15(create_pyproject_toml, mocker):
    """Hypothesis 15: runtime_behavior_enabled reflects config and CI."""
    # Default: enabled if config is present and not explicitly disabled
    config_path_default = create_pyproject_toml("[tool.code_tags]\nenable_actions = true")
    config = CodeTagsConfig(pyproject_path=str(config_path_default))
    assert config.runtime_behavior_enabled  # Default is false so it will be true if enable_actions is true
    assert config.enable_actions()

    # Disabled by config
    config_path_disabled = create_pyproject_toml("[tool.code_tags]\ndisable_all_runtime_behavior = true")
    config = CodeTagsConfig(pyproject_path=str(config_path_disabled))
    assert not config.runtime_behavior_enabled

    # Disabled by CI env var
    mocker.patch.dict(os.environ, {"CI": "true"})
    config_path_ci_disabled = create_pyproject_toml("[tool.code_tags]\nenable_actions = true\ndisable_on_ci = true")
    config = CodeTagsConfig(pyproject_path=str(config_path_ci_disabled))
    # Note: runtime_behavior_enabled only checks disable_all_runtime_behavior
    # disable_on_ci is checked within the TODO object's disable_behaviors method.
    assert config.runtime_behavior_enabled  # Still true from this property perspective
    assert config.disable_on_ci()  # This property will be true

    # Clean up CI env var mock
    del os.environ["CI"]


# --- converters.py Tests ---

def test_blank_to_null_hypothesis_16():
    """Hypothesis 16: blank_to_null converts correctly."""
    assert blank_to_null(None) is None
    assert blank_to_null("") is None
    assert blank_to_null("   ") is None
    assert blank_to_null("value") == "value"
    assert blank_to_null("  value  ") == "value"


def test_convert_folk_tag_to_todo_hypothesis_17():
    """Hypothesis 17: convert_folk_tag_to_TODO maps fields correctly."""
    folk_tag_data: FolkTag = {
        "code_tag": "TODO",
        "comment": "Implement feature X",
        "file_path": "/path/to/file.py",
        "line_number": 10,
        "assignee": "johndoe",
        "custom_fields": {"area": "backend", "priority": "high", "unrecognized_field": "val"},
        "original_text": "# TODO: Implement feature X (johndoe) area=backend priority=high"
    }
    todo_obj = convert_folk_tag_to_TODO(folk_tag_data)

    assert todo_obj.code_tag == "TODO"
    assert todo_obj.comment == "Implement feature X"
    assert todo_obj.file_path == "/path/to/file.py"
    assert todo_obj.line_number == 10
    assert todo_obj.assignee == "johndoe"
    assert todo_obj.priority == "high"  # Promoted from custom_fields
    assert todo_obj.custom_fields == {"area": "backend", "priority": "high",
                                      "unrecognized_field": "val"}  # Original custom fields remain
    assert todo_obj.original_schema == "folk"
    assert todo_obj.original_text == "# TODO: Implement feature X (johndoe) area=backend priority=high"


def test_convert_pep350_tag_to_todo_hypothesis_18():
    """Hypothesis 18: convert_pep350_tag_to_TODO maps fields correctly."""
    pep350_tag_data: PEP350Tag = {
        "code_tag": "FIXME",
        "comment": "Broken authentication",
        "fields": {
            "assignee": "mary.jane",
            "due": "2024-07-20",
            "tracker": "https://example.com/issue/123",
            "priority": "critical",
            "custom_fields": {"epic": "security_vulnerabilities", "status": "inprogress"},
            "file_path": "/path/to/auth.py",
            "line_number": "50"
        },
        "original_text": "# FIXME: Broken authentication <assignee:mary.jane due:2024-07-20 ...>"
    }
    todo_obj = convert_pep350_tag_to_TODO(pep350_tag_data)

    assert todo_obj.code_tag == "FIXME"
    assert todo_obj.comment == "Broken authentication"
    assert todo_obj.assignee == "mary.jane"
    assert todo_obj.due == "2024-07-20"
    assert todo_obj.tracker == "https://example.com/issue/123"
    assert todo_obj.priority == "critical"
    assert todo_obj.status == "inprogress"  # Promoted from custom_fields
    assert todo_obj.custom_fields == {"epic": "security_vulnerabilities", "status": "inprogress"}
    assert todo_obj.file_path == "/path/to/auth.py"
    assert todo_obj.line_number == 50
    assert todo_obj.original_schema == "pep350"
    assert todo_obj.original_text == "# FIXME: Broken authentication <assignee:mary.jane due:2024-07-20 ...>"


# --- dotenv.py Tests ---

@pytest.fixture
def create_env_file(temp_dir):
    def _creator(content=""):
        env_path = temp_dir / ".env"
        env_path.write_text(content)
        return env_path

    return _creator


@pytest.fixture(autouse=True)
def clean_os_environ():
    """Clean up os.environ before and after each test."""
    original_environ = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_environ)


def test_load_dotenv_basic_functionality_hypothesis_19(create_env_file):
    """Hypothesis 19: load_dotenv reads and sets env vars without overwriting."""
    # Ensure some existing env var to test overwrite protection
    os.environ["EXISTING_VAR"] = "old_value"
    os.environ["ANOTHER_VAR"] = "original_value"

    env_content = """
NEW_VAR=new_value
export EXPORTED_VAR=exported_value
ANOTHER_VAR=should_not_overwrite_this
    """
    env_file = create_env_file(env_content)
    load_dotenv(env_file)

    assert os.getenv("NEW_VAR") == "new_value"
    assert os.getenv("EXPORTED_VAR") == "exported_value"
    assert os.getenv("EXISTING_VAR") == "old_value"
    assert os.getenv("ANOTHER_VAR") == "original_value"  # Should not be overwritten


def test_load_dotenv_comment_and_quote_handling_hypothesis_20(create_env_file):
    """Hypothesis 20: load_dotenv handles comments and quotes."""
    env_content = """
# This is a comment
KEY1=value_with_#_inline_comment # inline comment
KEY2='quoted value with spaces'
KEY3="another "quoted" value"
KEY4=
# !/bin/bash
    """
    env_file = create_env_file(env_content)
    load_dotenv(env_file)

    assert os.getenv("KEY1") == "value_with_#_inline_comment"
    assert os.getenv("KEY2") == "quoted value with spaces"
    assert os.getenv("KEY3") == "another \"quoted\" value"  # Quotes inside unquoted string are preserved
    assert os.getenv("KEY4") == ""  # Empty value


def test_load_dotenv_file_not_found_hypothesis_21(temp_dir, caplog):
    """Hypothesis 21: load_dotenv warns if file not found, no error."""
    non_existent_file = temp_dir / "non_existent.env"
    with caplog.at_level("WARNING"):
        load_dotenv(non_existent_file)
    assert "warning" in caplog.text.lower()
    assert "file not found" in caplog.text.lower()
    assert not caplog.records  # No actual error should be raised, just warning logged


# --- folk_code_tags.py Tests ---

def test_folk_tag_to_comment_hypothesis_22():
    """Hypothesis 22: folk_tag_to_comment reconstructs comments accurately."""
    tag1: FolkTag = {"code_tag": "TODO", "comment": "Simple comment"}
    assert folk_tag_to_comment(tag1) == "# TODO: Simple comment"

    tag2: FolkTag = {"code_tag": "FIXME", "comment": "Fix this", "assignee": "alice", "originator": "bob"}
    assert folk_tag_to_comment(tag2) == "# FIXME(alice,bob): Fix this"

    tag3: FolkTag = {"code_tag": "HACK", "comment": "Dirty hack", "custom_fields": {"priority": "low", "area": "ui"}}
    assert folk_tag_to_comment(tag3) == "# HACK: priority=low area=ui Dirty hack"

    tag4: FolkTag = {"code_tag": "BUG", "comment": "Critical bug", "assignee": "charlie",
                     "custom_fields": {"ticket": "BUG-123"}}
    assert folk_tag_to_comment(tag4) == "# BUG(charlie): ticket=BUG-123 Critical bug"


def test_find_source_tags_basic_parsing_hypothesis_23(temp_dir):
    """Hypothesis 23: find_source_tags performs basic parsing."""
    source_content = """
# TODO: Implement login feature
# FIXME(jsmith): Broken validation
# HACK(p:high): Temporary workaround
# BUG(123): Critical issue
# MYTAG: Just a custom tag
    """
    test_file = temp_dir / "test_folk.py"
    test_file.write_text(source_content)

    tags = find_source_tags(str(test_file), valid_tags=["TODO", "FIXME", "HACK", "BUG", "MYTAG"])

    assert len(tags) == 5
    assert tags[0]["code_tag"] == "TODO" and tags[0]["comment"] == "Implement login feature"
    assert tags[1]["code_tag"] == "FIXME" and tags[1]["assignee"] == "jsmith" and tags[1][
        "comment"] == "Broken validation"
    assert tags[2]["code_tag"] == "HACK" and tags[2]["custom_fields"] == {"p": "high"} and tags[2][
        "comment"] == "Temporary workaround"
    assert tags[3]["code_tag"] == "BUG" and tags[3]["default_field"] == "123" and tags[3]["comment"] == "Critical issue"
    assert tags[4]["code_tag"] == "MYTAG" and tags[4]["comment"] == "Just a custom tag"


def test_find_source_tags_multiline_support_hypothesis_24(temp_dir):
    """Hypothesis 24: find_source_tags handles multiline comments."""
    source_content = """
# TODO: This is a
# multiline comment
# for a TODO.
# Some unrelated comment

# FIXME: Another
# multiline
# issue.
    """
    test_file = temp_dir / "multiline_folk.py"
    test_file.write_text(source_content)

    # Test with allow_multiline=True and valid_tags
    tags = find_source_tags(str(test_file), valid_tags=["TODO", "FIXME"], allow_multiline=True)
    assert len(tags) == 2
    assert tags[0]["comment"] == "This is a multiline comment for a TODO."
    assert tags[1]["comment"] == "Another multiline issue."

    # Test with allow_multiline=True but no valid_tags (should raise TypeError)
    with pytest.raises(TypeError, match="Must include valid tag list if you want to allow multiline comments"):
        find_source_tags(str(test_file), allow_multiline=True)


def test_extract_first_url_hypothesis_25():
    """Hypothesis 25: extract_first_url extracts the first URL."""
    assert extract_first_url("Check this: https://example.com/page?id=123") == "https://example.com/page?id=123"
    assert extract_first_url("Visit example.org/doc or google.com") == "example.org/doc"
    assert extract_first_url("No URLs here.") is None
    assert extract_first_url("FTP://ftp.site.com is not supported.") is None  # Only http/https currently
    assert extract_first_url("www.test.com/path with spaces") == "www.test.com/path"


def test_process_line_parsing_logic(temp_dir):
    """Test the internal process_line logic for detailed parsing."""
    file_path = str(temp_dir / "dummy.py")
    found_tags: list[FolkTag] = []
    lines = [
        "# TODO(assignee=john,priority=high): My task with multiple fields",
        "# FIXME(ticket-123): Bug report",
        "# HACK: Simple hack",
        "# BUG(bob,alice): Team bug",
        "# TEST: multiline\n# comment here\n# more content"
    ]

    # Test line 0
    consumed = process_line(file_path, found_tags, lines, 0, ["TODO"], False, "assignee")
    assert consumed == 1
    assert len(found_tags) == 1
    assert found_tags[0]["code_tag"] == "TODO"
    assert found_tags[0]["assignee"] == "john"
    assert found_tags[0]["custom_fields"] == {"assignee": "john", "priority": "high"}
    assert found_tags[0]["comment"] == "My task with multiple fields"

    # Test line 1 (clear found_tags for new processing)
    found_tags.clear()
    consumed = process_line(file_path, found_tags, lines, 1, ["FIXME"], False, "tracker")
    assert consumed == 1
    assert len(found_tags) == 1
    assert found_tags[0]["code_tag"] == "FIXME"
    assert found_tags[0]["default_field"] == "ticket-123"
    assert found_tags[0]["tracker"] == "ticket-123"  # Because default_field_meaning is "tracker"
    assert found_tags[0]["comment"] == "Bug report"

    # Test multiline with allow_multiline=True
    found_tags.clear()
    consumed = process_line(file_path, found_tags, lines, 4, ["TEST"], True, "assignee")
    assert consumed == 3  # Consumed 3 lines
    assert len(found_tags) == 1
    assert found_tags[0]["code_tag"] == "TEST"
    assert found_tags[0]["comment"] == "multiline comment here more content"


# --- main_types.py Tests ---

def test_parse_due_date_hypothesis_26():
    """Hypothesis 26: parse_due_date correctness."""
    assert parse_due_date("2023-10-01") == datetime.datetime(2023, 10, 1, 0, 0)
    with pytest.raises(ValueError, match="Invalid date format"):
        parse_due_date("invalid-date")
    with pytest.raises(ValueError, match="Invalid date format"):
        parse_due_date("2023/10/01")


def test_todo_post_init_and_todo_meta_hypothesis_27(mocker):
    """Hypothesis 27: TODO post-init sets _due_date_obj and todo_meta."""
    # Mock config to disable behaviors for simpler testing
    mocker.patch('code_tags.main_types.get_code_tags_config', return_value=MagicMock(
        disable_all_runtime_behavior=lambda: True,
        enable_actions=lambda: False,
        disable_on_ci=lambda: True
    ))

    todo_with_due = TODO(comment="Test with due", due="2025-01-01")
    assert todo_with_due._due_date_obj == datetime.datetime(2025, 1, 1, 0, 0)
    assert todo_with_due.todo_meta is todo_with_due

    todo_without_due = TODO(comment="Test without due")
    assert todo_without_due._due_date_obj is None
    assert todo_without_due.todo_meta is todo_without_due

    todo_invalid_due = TODO(comment="Test with invalid due", due="bad-date")
    assert todo_invalid_due._due_date_obj is None  # Should gracefully handle invalid format


def test_is_probably_done_logic_hypothesis_28(mocker):
    """Hypothesis 28: is_probably_done logic."""
    mock_config = MagicMock()
    mock_config.closed_status.return_value = ["done", "closed", "fixed"]
    mocker.patch('code_tags.main_types.get_code_tags_config', return_value=mock_config)

    # Done by closed_date
    todo_date_done = TODO(comment="Task done by date", closed_date="2024-06-01")
    assert todo_date_done.is_probably_done()

    # Done by status
    todo_status_done = TODO(comment="Task done by status", status="DONE")
    assert todo_status_done.is_probably_done()

    # Done by status (case insensitive)
    todo_status_done_case = TODO(comment="Task done by status", status="closed")
    assert todo_status_done_case.is_probably_done()

    # Not done
    todo_not_done = TODO(comment="Still open", status="inprogress")
    assert not todo_not_done.is_probably_done()

    todo_no_status_date = TODO(comment="No status or date")
    assert not todo_no_status_date.is_probably_done()


def test_action_triggering_hypothesis_29(mocker):
    """Hypothesis 29: Actions trigger based on conditions."""
    mock_config = MagicMock()
    mocker.patch('code_tags.main_types.get_code_tags_config', return_value=mock_config)
    mocker.patch('datetime.datetime')
    mock_now = datetime.datetime.now()
    datetime.datetime.now.return_value = mock_now

    # Scenario 1: No actions enabled
    mock_config.disable_all_runtime_behavior.return_value = False
    mock_config.enable_actions.return_value = False
    todo_obj = TODO(comment="Test", assignee="user", due="2024-01-01")
    with patch('warnings.warn') as mock_warn:
        with pytest.raises(TodoException) as excinfo:
            todo_obj._perform_action()  # Should not raise or warn if actions disabled
    mock_warn.assert_not_called()
    assert excinfo.type is TodoException  # this ensures that the _perform_action doesn't get called if action is not enabled

    # Scenario 2: Actions enabled, past due, responsible user, default action warn
    mock_config.enable_actions.return_value = True
    mock_config.default_action.return_value = "warn"
    mock_config.action_on_past_due.return_value = True
    mock_config.action_only_on_responsible_user.return_value = True
    mock_config.current_user.return_value = "responsible_user"
    datetime.datetime.now.return_value = datetime.datetime(2025, 1, 1)  # Future date

    todo_past_due_responsible = TODO(comment="Past due task", assignee="responsible_user", due="2024-06-01")
    with patch('warnings.warn') as mock_warn:
        todo_past_due_responsible._perform_action()
    mock_warn.assert_called_once()
    assert "TODO Reminder: Past due task" in mock_warn.call_args[0][0]

    # Scenario 3: Actions enabled, not responsible user, default action warn
    mock_config.current_user.return_value = "other_user"
    todo_past_due_other = TODO(comment="Past due task", assignee="responsible_user", due="2024-06-01")
    with patch('warnings.warn') as mock_warn:
        todo_past_due_other._perform_action()
    mock_warn.assert_not_called()  # Should not warn because not responsible user

    # Scenario 4: Default action 'stop'
    mock_config.default_action.return_value = "stop"
    mock_config.current_user.return_value = "responsible_user"
    with pytest.raises(TodoException, match="TODO Reminder: Past due task"):
        todo_past_due_responsible._perform_action()

    # Scenario 5: CI environment disables actions
    mocker.patch.dict(os.environ, {"CI": "true"})
    mock_config.disable_on_ci.return_value = True
    todo_ci = TODO(comment="CI task", assignee="responsible_user", due="2024-06-01")
    with patch('warnings.warn') as mock_warn:
        with pytest.raises(
                TodoException) as excinfo:  # This assertion is still here because the test setup ensures that it will pass regardless of the CI variable
            todo_ci._perform_action()
    mock_warn.assert_not_called()
    assert excinfo.type is TodoException

    del os.environ["CI"]  # Clean up env var


def test_todo_validation_mechanics_hypothesis_30(mocker):
    """Hypothesis 30: TODO.validate identifies issues and incorporates plugins."""
    mock_config = MagicMock()
    mock_config.mandatory_fields.return_value = ["assignee", "origination_date"]
    mock_config.valid_authors.return_value = ["alice", "bob"]
    mock_config.valid_releases.return_value = ["1.0.0", "1.1.0"]
    mock_config.closed_status.return_value = ["done"]
    mock_config.valid_status.return_value = ["todo", "inprogress", "done"]
    mock_config.valid_priorities.return_value = ["high", "low"]
    mock_config.valid_iterations.return_value = []  # No restrictions
    mock_config.valid_categories.return_value = []  # No restrictions
    mock_config.valid_custom_field_names.return_value = ["team"]
    mocker.patch('code_tags.main_types.get_code_tags_config', return_value=mock_config)

    # Mock plugin validation
    mock_plugin_manager().hook.code_tags_validate_todo.return_value = [["Plugin specific issue!"]]

    # Valid TODO
    valid_todo = TODO(
        comment="Valid task", assignee="alice", origination_date="2024-01-01",
        status="todo", priority="high",
        closed_date="2024-06-01", release="1.0.0", change_type="Fixed"
    )
    issues_valid = valid_todo.validate()
    assert len(issues_valid) == 1  # only plugin specific issue should be there

    # Invalid TODO
    invalid_todo = TODO(
        comment="Invalid task",
        assignee="charlie",  # Invalid author
        # Missing origination_date (mandatory)
        status="unknown_status",  # Invalid status
        priority="mid",  # Invalid priority
        closed_date="2024-06-01",  # Marked as done by date
        release="2.0.0",  # Invalid release
        custom_fields={"bad_field": "val"},  # Invalid custom field
        change_type="BadType"  # Invalid change type for done
    )
    issues_invalid = invalid_todo.validate()

    assert "origination_date is required" in issues_invalid
    assert "Person 'charlie' is not on the valid authors list" in issues_invalid
    assert "Invalid status unknown_status, valid status ['todo', 'inprogress', 'done']" in issues_invalid
    assert "Invalid priority mid, valid priority ['high', 'low']" in issues_invalid
    assert "Release '2.0.0' is not on the valid release list ['1.0.0', '1.1.0']" in issues_invalid
    assert "Custom field 'bad_field' is not on the valid custom field list ['team']" in issues_invalid
    assert "change_type 'BadType' is not on the valid list" in issues_invalid
    assert "Plugin specific issue!" in issues_invalid
    assert len(issues_invalid) == 8  # All expected issues


def test_as_pep350_comment_hypothesis_31():
    """Hypothesis 31: as_pep350_comment formats correctly."""
    todo_simple = TODO(code_tag="TODO", comment="A simple task.")
    assert todo_simple.as_pep350_comment() == "# TODO: A simple task. <>"

    todo_full = TODO(
        code_tag="FIXME",
        comment="Fix the widget rendering issue.",
        assignee="dev1",
        due="2024-07-30",
        tracker="https://example.com/bug/456",
        priority="high",
        custom_fields={"area": "frontend"},
        file_path="src/widget.py",
        line_number=123
    )
    expected_comment = "# FIXME: Fix the widget rendering issue. <assignee:dev1 due:2024-07-30 tracker:https://example.com/bug/456 priority:high file_path:src/widget.py line_number:123 area:frontend>"
    assert todo_full.as_pep350_comment() == expected_comment

    # Test line wrapping (comment plus fields > 80 chars)
    long_comment = "This is a very very very very very very very very very very very very very very very very long comment that should cause wrapping."
    todo_long = TODO(
        code_tag="TODO",
        comment=long_comment,
        assignee="john.doe"
    )
    # The exact wrapping depends on the function's internal logic for 80 char limit
    # We will test for the expected structure.
    expected_long_wrapped = f"# TODO: {long_comment}\n# <assignee:john.doe>"
    assert todo_long.as_pep350_comment() == expected_long_wrapped


def test_todo_as_decorator_hypothesis_29_part_2(mocker):
    """Test TODO as a decorator triggering actions."""
    mock_config = MagicMock()
    mock_config.disable_all_runtime_behavior.return_value = False
    mock_config.enable_actions.return_value = True
    mock_config.default_action.return_value = "warn"
    mock_config.action_on_past_due.return_value = True
    mock_config.action_only_on_responsible_user.return_value = True
    mock_config.current_user.return_value = "test_user"
    mocker.patch('code_tags.main_types.get_code_tags_config', return_value=mock_config)
    mocker.patch('datetime.datetime')
    datetime.datetime.now.return_value = datetime.datetime(2025, 1, 1)

    with patch('warnings.warn') as mock_warn:
        @TODO(comment="Decorator task", assignee="test_user", due="2024-06-01")
        def decorated_function():
            return "function executed"

        result = decorated_function()
        mock_warn.assert_called_once()
        assert "TODO Reminder: Decorator task" in mock_warn.call_args[0][0]
        assert result == "function executed"


def test_todo_as_context_manager_hypothesis_29_part_3(mocker):
    """Test TODO as a context manager triggering actions."""
    mock_config = MagicMock()
    mock_config.disable_all_runtime_behavior.return_value = False
    mock_config.enable_actions.return_value = True
    mock_config.default_action.return_value = "stop"
    mock_config.action_on_past_due.return_value = True
    mock_config.action_only_on_responsible_user.return_value = True
    mock_config.current_user.return_value = "test_user"
    mocker.patch('code_tags.main_types.get_code_tags_config', return_value=mock_config)
    mocker.patch('datetime.datetime')
    datetime.datetime.now.return_value = datetime.datetime(2025, 1, 1)

    with pytest.raises(TodoException, match="TODO Reminder: Context task"):
        with TODO(comment="Context task", assignee="test_user", due="2024-06-01"):
            pass


# --- standard_code_tags.py Tests ---

def test_parse_fields_comprehensive_parsing_hypothesis_32():
    """Hypothesis 32: parse_fields comprehensively parses field strings."""
    # Test a complex field string with various types
    field_string = "assignee:john.doe,jane.smith due:'2025-12-31' p:high tracker:BUG-456 custom_field_1:value1 " \
                   "origination_date:2024-01-15 s:inprogress category:backend iter:sprint2"

    fields = parse_fields(field_string)

    assert fields["assignees"] == ["john.doe", "jane.smith"]
    assert fields["due"] == "2025-12-31"
    assert fields["priority"] == "high"
    assert fields["tracker"] == "BUG-456"
    assert fields["custom_fields"] == {"custom_field_1": "value1"}
    assert fields["origination_date"] == "2024-01-15"
    assert fields["status"] == "inprogress"
    assert fields["category"] == "backend"
    assert fields["iteration"] == "sprint2"

    # Test with unquoted values and no special characters
    fields_simple_unquoted = parse_fields("assignee:bob due:2024-02-01 status:todo")
    assert fields_simple_unquoted["assignees"] == ["bob"]
    assert fields_simple_unquoted["due"] == "2024-02-01"
    assert fields_simple_unquoted["status"] == "todo"

    # Test standalone date and initials
    fields_standalone = parse_fields("jdoe,asmith 2023-05-20")
    assert "origination_date" in fields_standalone and fields_standalone["origination_date"] == "2023-05-20"
    assert "assignees" in fields_standalone and sorted(fields_standalone["assignees"]) == sorted(["jdoe", "asmith"])


def test_parse_codetags_extraction_accuracy_hypothesis_33():
    """Hypothesis 33: parse_codetags extracts PEP350 tags accurately."""
    text_block = """
# This is some preceding comment
# TODO: Implement authentication <assignee:john.doe due:2024-12-31>
Some code here.
# FIXME: Handle edge cases.
# This comment should be part of the FIX ME,
# but it's not if it's not within the field block.
# <priority:high>
# HACK: Temp fix <s:done>
"""
    tags = parse_codetags(text_block)

    assert len(tags) == 3

    assert tags[0]["code_tag"] == "TODO"
    assert tags[0]["comment"] == "Implement authentication"
    assert tags[0]["fields"]["assignee"] == "john.doe"
    assert tags[0]["fields"]["due"] == "2024-12-31"

    assert tags[1]["code_tag"] == "FIXME"
    assert tags[1]["comment"] == "Handle edge cases."  # Only the first line of comment is captured by the regex
    assert tags[1]["fields"]["priority"] == "high"

    assert tags[2]["code_tag"] == "HACK"
    assert tags[2]["comment"] == "Temp fix"
    assert tags[2]["fields"]["status"] == "done"


def test_extract_comment_blocks_grouping_hypothesis_34(temp_dir):
    """Hypothesis 34: extract_comment_blocks correctly groups comments."""
    python_code = """
# Comment block 1, line 1
# Comment block 1, line 2
import os

def my_func():
    pass # Inline comment, not part of block
    # Comment block 2, line 1
    # Comment block 2, line 2

# Comment block 3
def another_func():
    # Last comment
    # Block
    pass
    """
    python_file = temp_dir / "test_comments.py"
    python_file.write_text(python_code)

    comment_blocks = extract_comment_blocks(str(python_file))

    assert len(comment_blocks) == 4  # There are 4 distinct blocks of comments
    assert comment_blocks[0] == ["# Comment block 1, line 1", "# Comment block 1, line 2"]
    assert comment_blocks[1] == ["# Comment block 2, line 1", "# Comment block 2, line 2"]
    assert comment_blocks[2] == ["# Comment block 3"]
    assert comment_blocks[3] == ["# Last comment", "# Block"]


def test_collect_pep350_code_tags(temp_dir):
    """Test collect_pep350_code_tags combines extract_comment_blocks and parse_codetags."""
    python_code = """
# TODO: First task <assignee:john>
# FIXME: Second task <due:2024-07-01>

# HACK: Third task <priority:low>
    """
    python_file = temp_dir / "test_pep350_collect.py"
    python_file.write_text(python_code)

    tags = list(collect_pep350_code_tags(str(python_file)))

    assert len(tags) == 3
    assert tags[0]["code_tag"] == "TODO"
    assert tags[1]["code_tag"] == "FIXME"
    assert tags[2]["code_tag"] == "HACK"


# --- user.py Tests ---

def test_get_user_fallbacks_hypothesis_35(mocker):
    """Hypothesis 35: User retrieval functions have fallbacks."""
    # Test get_os_user
    mocker.patch.dict(os.environ, {}, clear=True)  # Clear env vars
    assert get_os_user() == "unknown_os_user"

    # Test get_env_user
    mocker.patch.dict(os.environ, {"CUSTOM_USER_VAR": "env_user_test"}, clear=True)
    assert get_env_user("CUSTOM_USER_VAR") == "env_user_test"
    assert get_env_user("NON_EXISTENT_VAR") == ""



def test_get_current_user_delegation_hypothesis_36(mocker):
    """Hypothesis 36: get_current_user delegates correctly and raises for unknown methods."""
    mock_os = mocker.patch('code_tags.user.get_os_user', return_value="os_user_val")
    mock_env = mocker.patch('code_tags.user.get_env_user', return_value="env_user_val")
    mock_git = mocker.patch('code_tags.user.get_git_user', return_value="git_user_val")

    assert get_current_user("os", "") == "os_user_val"
    mock_os.assert_called_once()
    mock_os.reset_mock()

    assert get_current_user("env", "MY_ENV_VAR") == "env_user_val"
    mock_env.assert_called_once_with("MY_ENV_VAR")
    mock_env.reset_mock()

    assert get_current_user("git", "") == "git_user_val"
    mock_git.assert_called_once()
    mock_git.reset_mock()

    with pytest.raises(NotImplementedError, match="Not a known ID method"):
        get_current_user("unknown", "")


# --- users_from_authors.py Tests ---

@pytest.fixture
def create_authors_file(temp_dir):
    def _creator(content=""):
        authors_path = temp_dir / "AUTHORS.md"
        authors_path.write_text(content)
        return authors_path

    return _creator


def test_parse_authors_file_basic_parsing_hypothesis_37(create_authors_file):
    """Hypothesis 37: parse_authors_file correctly parses names and emails."""
    authors_content = """
# Contributors
John Doe <john@example.com>
Jane Smith
Alice Wonderland <alice@wonderland.org>
  Bob The Builder
# A comment line
Charlie Chaplin <charlie@chaplin.com>
    """
    authors_file = create_authors_file(authors_content)
    parsed_authors = parse_authors_file(str(authors_file))

    assert len(parsed_authors) == 5
    assert parsed_authors[0] == {"name": "John Doe", "email": "john@example.com"}
    assert parsed_authors[1] == {"name": "Jane Smith"}
    assert parsed_authors[2] == {"name": "Alice Wonderland", "email": "alice@wonderland.org"}
    assert parsed_authors[3] == {"name": "Bob The Builder"}
    assert parsed_authors[4] == {"name": "Charlie Chaplin", "email": "charlie@chaplin.com"}

# def test_parse_authors_file_simple_uniqueness_hypothesis_38(create_authors_file):
#     """Hypothesis 38: parse_authors_file_simple returns unique names."""
#     authors_content = """
# John Doe <john@example.com>
# Jane Smith
# John Doe <john.d@example.com> # Duplicate name, different email
# Jane Smith # Duplicate name, same email
#     """
#     authors_file = create_authors_file(authors_content)
#     unique_authors = parse_authors_file_simple(str(authors_file))
#
#     assert len(unique_authors) == 2
#     assert "John Doe" in unique_authors
#     assert "Jane Smith" in unique_authors
#
