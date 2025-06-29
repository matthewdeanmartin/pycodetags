import ast
import importlib.util
import logging
import sys
import textwrap
import types
from pathlib import Path

import pytest

from pycodetags.collect_ast import TodoExceptionCollector
from pycodetags.todo_tag_types import TodoException

logger = logging.getLogger(__name__)


def make_module(tmp_path: Path, code: str, name: str = "mod") -> types.ModuleType:
    """Helper: writes code to .py file and loads it as a module."""
    file_path = tmp_path / f"{name}.py"
    file_path.write_text(textwrap.dedent(code), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, file_path)
    mod = importlib.util.module_from_spec(spec)
    mod.__spec__ = spec
    mod.__file__ = str(file_path)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_no_file_attr():
    coll = TodoExceptionCollector()
    mod = types.ModuleType("no_file_mod")
    if hasattr(mod, "__file__"):
        delattr(mod, "__file__")
    assert not coll.collect_from_source_analysis(mod)


def test_file_is_none(monkeypatch):
    coll = TodoExceptionCollector()
    mod = types.ModuleType("nil_file_mod")
    mod.__file__ = None
    assert not coll.collect_from_source_analysis(mod)


def test_no_raises(tmp_path):
    code = """
    def foo():
        return 1
    """
    mod = make_module(tmp_path, code, name="no_raises")
    coll = TodoExceptionCollector()
    assert not coll.collect_from_source_analysis(mod)

@pytest.mark.skipif(sys.version_info < (3, 8), reason="Requires Python > 3.7")
def test_single_todo_raise_full_args(tmp_path):
    # include assignee, due, message
    code = """
    from pycodetags.todo_tag_types import TodoException
    def foo():
        raise TodoException(assignee='alice', due='2025-12-31', message='fix this')
    """
    mod = make_module(tmp_path, code, name="full_args")
    coll = TodoExceptionCollector()
    results = coll.collect_from_source_analysis(mod)
    assert len(results) == 1
    exc = results[0]
    assert isinstance(exc, TodoException)
    assert exc.assignee == "alice"
    assert exc.due == "2025-12-31"
    assert exc.message == "fix this"

@pytest.mark.skipif(sys.version_info < (3, 8), reason="Requires Python > 3.7")
def test_partial_args(tmp_path):
    code = """
    from pycodetags.todo_tag_types import TodoException
    def foo():
        raise TodoException(assignee='bob', message='oh no')
    """
    mod = make_module(tmp_path, code, name="partial_args")
    coll = TodoExceptionCollector()
    results = coll.collect_from_source_analysis(mod)
    assert len(results) == 1
    exc = results[0]
    assert exc.assignee == "bob"
    assert getattr(exc, "due_date", None) is None
    assert getattr(exc, "message", None) == "oh no"


def test_raise_non_todo(tmp_path):
    code = """
    def foo():
        raise ValueError('oops')
    """
    mod = make_module(tmp_path, code, name="other_raise")
    coll = TodoExceptionCollector()
    assert not coll.collect_from_source_analysis(mod)


def test_unicode_decode_error(tmp_path, monkeypatch):
    # create file with invalid utf-8 bytes
    file_path = tmp_path / "badenc.py"
    file_path.write_bytes(b"\xff\xfe\xfa")
    spec = importlib.util.spec_from_file_location("badenc", file_path)
    mod = types.ModuleType("badenc")
    mod.__spec__ = spec
    mod.__file__ = str(file_path)
    sys.modules["badenc"] = mod

    coll = TodoExceptionCollector()
    # reading triggers UnicodeDecodeError
    assert not coll.collect_from_source_analysis(mod)


@pytest.mark.skipif(sys.version_info < (3, 8), reason="Requires Python > 3.7")
def test_extract_args_legacy_str(monkeypatch):
    # craft AST call node with ast.Str
    src = "TodoException(assignee='u', due='d', message='m')"
    expr = ast.parse(src, mode="eval").body
    coll = TodoExceptionCollector()
    args = coll._extract_exception_args(expr)
    assert args == {"assignee": "u", "due": "d", "message": "m"}


def test_extract_args_ignore_non_constants():
    src = "TodoException(assignee=unknown)"
    expr = ast.parse(src, mode="eval").body
    coll = TodoExceptionCollector()
    args = coll._extract_exception_args(expr)
    assert not args
