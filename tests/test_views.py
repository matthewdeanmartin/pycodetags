# tests/test_views.py

import io
import json
from contextlib import redirect_stdout

import pytest

from pycodetags.data_tags_classes import DATA
from pycodetags.views import print_data_md, print_html, print_json, print_text, print_validate


@pytest.fixture
def sample_data():
    return [
        DATA(
            code_tag="TODO",
            comment="Implement feature X",
            data_fields={"priority": "high"},
            default_fields={"originator": "JD"},
            custom_fields={"team": "alpha"},
            file_path="project/module.py",
            line_number=10,
        ),
        DATA(
            code_tag="DONE",
            comment="Refactor feature Y",
            data_fields={"priority": "low"},
            default_fields={"originator": "AL"},
            custom_fields={},
            file_path="project/module.py",
            line_number=20,
        ),
    ]


def test_print_validate(sample_data):
    # Override validate() to return dummy errors for testing
    sample_data[0].validate = lambda: ["Missing something"]
    sample_data[1].validate = lambda: []

    buf = io.StringIO()
    with redirect_stdout(buf):
        print_validate(sample_data)

    output = buf.getvalue()
    assert "TODO" in output
    assert "Missing something" in output
    assert "DONE" not in output  # No validation errors, so shouldn't appear


def test_print_html(sample_data):
    buf = io.StringIO()
    buf.seek(0)
    with redirect_stdout(buf):
        print_html(sample_data)

    output = buf.getvalue()
    assert "<h1>TODO</h1>" in output
    assert "<strong>Implement feature X</strong>" in output
    assert "<h1>DONE</h1>" in output


def test_print_text(sample_data):
    buf = io.StringIO()
    buf.seek(0)
    with redirect_stdout(buf):
        print_text(sample_data)

    output = buf.getvalue()
    assert "--- TODO ---" in output
    assert "Implement feature X" in output
    assert "--- DONE ---" in output
    assert "Refactor feature Y" in output


def test_print_json(sample_data):
    buf = io.StringIO()
    buf.seek(0)
    with redirect_stdout(buf):
        print_json(sample_data)

    output = buf.getvalue()
    # Validate it's valid JSON
    json_start = output.find("[")
    parsed = json.loads(output[json_start:])
    assert isinstance(parsed, list)
    assert any("comment" in item for item in parsed)


def test_print_data_md(sample_data):
    buf = io.StringIO()
    with redirect_stdout(buf):
        print_data_md(sample_data)

    output = buf.getvalue()
    assert "project/module.py" in output
    assert "```python" in output
    assert "TODO" in output
    assert "DONE" in output
