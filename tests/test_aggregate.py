# tests/test_aggregate.py

import sys
import textwrap
from pathlib import Path

import pytest

from pycodetags import PureDataSchema
from pycodetags.aggregate import aggregate_all_kinds, aggregate_all_kinds_multiple_input
from pycodetags.data_tags_classes import DATA
from pycodetags.exceptions import FileParsingError


def create_python_file(path: Path, content: str) -> Path:
    file_path = path / "sample.py"
    file_path.write_text(content)
    return file_path


def test_aggregate_from_source_file(tmp_path):
    # Create a source file with a valid TODO
    content = textwrap.dedent(
        """
        # TODO: Fix this bug <originator:JD origination_date:2024-01-01>
        def func():
            pass
    """
    )
    create_python_file(tmp_path, content)

    found_tags, found_data = aggregate_all_kinds(module_name="", source_path=str(tmp_path), schema=PureDataSchema)

    assert len(found_tags) >= 1
    assert all(tag["code_tag"] == "TODO" for tag in found_tags)
    assert isinstance(found_data, list)


def test_aggregate_all_kinds_multiple_input(tmp_path):
    # Same as above but test aggregate_all_kinds_multiple_input
    content = textwrap.dedent(
        """
        # TODO: Another fix <originator:AB origination_date:2024-06-01>
        def example():
            pass
    """
    )
    create_python_file(tmp_path, content)

    results = aggregate_all_kinds_multiple_input(module_names=[], source_paths=[str(tmp_path)], schema=PureDataSchema)
    assert isinstance(results, list)
    assert any(isinstance(item, DATA) for item in results)
    assert any(item.code_tag == "TODO" for item in results)


def test_aggregate_from_module(tmp_path):
    # Create a temporary module with a DATA-decorated function
    mod_path = tmp_path / "testmod"
    mod_path.mkdir()
    init_file = mod_path / "__init__.py"
    module_code = textwrap.dedent(
        """
        from pycodetags import DATA

        @DATA(comment="Module level item")
        def marked():
            pass
    """
    )
    init_file.write_text(module_code)

    sys.path.insert(0, str(tmp_path))
    try:
        _found_tags, found_data = aggregate_all_kinds(module_name="testmod", source_path="", schema=PureDataSchema)
        assert isinstance(found_data, list)
        assert any(isinstance(item, DATA) for item in found_data)
    finally:
        sys.path.pop(0)


def test_aggregate_with_empty_inputs(tmp_path):
    results = aggregate_all_kinds_multiple_input([], [], PureDataSchema)
    assert isinstance(results, list)
    assert len(results) == 0


def test_aggregate_raises_on_invalid_path(tmp_path):
    bad_path = tmp_path / "nonexistent"

    with pytest.raises(FileParsingError, match="Can't find any files in source folder"):
        aggregate_all_kinds(module_name="", source_path=str(bad_path), schema=PureDataSchema)
