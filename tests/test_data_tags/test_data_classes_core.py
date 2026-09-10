"""Tests for DATA class core behaviour: decorator, context manager, serialization, equality, terminal_link."""

from __future__ import annotations

import datetime

import pytest

from pycodetags.data_tags.data_tags_classes import DATA, Serializable
from pycodetags.exceptions import DataTagError, ValidationError

# ---------------------------------------------------------------------------
# Serializable.to_dict
# ---------------------------------------------------------------------------


class _SampleSerializable(Serializable):
    def __init__(self):
        self.name = "hello"
        self.when = datetime.datetime(2025, 1, 15, 12, 0, 0)
        self._private = "skip me"
        self.data_meta = "skip data_meta"


def test_to_dict_converts_datetime_to_iso():
    obj = _SampleSerializable()
    d = obj.to_dict()
    assert d["when"] == "2025-01-15T12:00:00"


def test_to_dict_omits_private_keys():
    obj = _SampleSerializable()
    d = obj.to_dict()
    assert "_private" not in d


def test_to_dict_omits_data_meta():
    obj = _SampleSerializable()
    d = obj.to_dict()
    assert "data_meta" not in d


def test_to_dict_keeps_regular_fields():
    obj = _SampleSerializable()
    d = obj.to_dict()
    assert d["name"] == "hello"


# ---------------------------------------------------------------------------
# DATA construction & data_meta self-reference
# ---------------------------------------------------------------------------


def test_data_post_init_sets_data_meta_to_self():
    tag = DATA(code_tag="TODO", comment="x")
    assert tag.data_meta is tag


def test_data_repr_excludes_data_meta():
    tag = DATA(code_tag="TODO", comment="x")
    r = repr(tag)
    assert "data_meta" not in r
    assert "TODO" in r


# ---------------------------------------------------------------------------
# DATA.__eq__
# ---------------------------------------------------------------------------


def test_data_eq_same_values():
    a = DATA(code_tag="TODO", comment="fix it")
    b = DATA(code_tag="TODO", comment="fix it")
    assert a == b


def test_data_eq_different_comment():
    a = DATA(code_tag="TODO", comment="a")
    b = DATA(code_tag="TODO", comment="b")
    assert a != b


def test_data_eq_different_code_tag():
    a = DATA(code_tag="TODO", comment="x")
    b = DATA(code_tag="FIXME", comment="x")
    assert a != b


# ---------------------------------------------------------------------------
# DATA decorator usage (__call__)
# ---------------------------------------------------------------------------


def test_data_as_decorator_calls_wrapped_function():
    tag = DATA(code_tag="TODO", comment="some work")
    call_log = []

    @tag
    def my_func():
        call_log.append("called")
        return 42

    result = my_func()
    assert result == 42
    assert call_log == ["called"]


def test_data_as_decorator_preserves_function_name():
    tag = DATA(code_tag="TODO", comment="annotated")

    @tag
    def important_function():
        pass

    assert important_function.__name__ == "important_function"


def test_data_as_decorator_attaches_data_meta():
    tag = DATA(code_tag="NOTE", comment="meta")

    @tag
    def fn():
        pass

    assert hasattr(fn, "data_meta")
    assert fn.data_meta is tag


# ---------------------------------------------------------------------------
# DATA context manager (__enter__ / __exit__)
# ---------------------------------------------------------------------------


def test_data_as_context_manager_returns_self():
    tag = DATA(code_tag="TODO", comment="ctx")
    with tag as ctx:
        assert ctx is tag


def test_data_context_manager_propagates_exceptions():
    tag = DATA(code_tag="TODO", comment="ctx")
    with pytest.raises(ValueError):
        with tag:
            raise ValueError("boom")


def test_data_context_manager_does_not_suppress_exceptions():
    tag = DATA(code_tag="FIXME", comment="suppress test")
    raised = False
    try:
        with tag:
            raise RuntimeError("propagated")
    except RuntimeError:
        raised = True
    assert raised


# ---------------------------------------------------------------------------
# DATA.validate / validate_or_raise
# ---------------------------------------------------------------------------


def test_validate_returns_empty_list_for_base_class():
    tag = DATA(code_tag="TODO", comment="x")
    assert tag.validate() == []


def test_validate_or_raise_does_not_raise_when_valid():
    tag = DATA(code_tag="TODO", comment="x")
    tag.validate_or_raise()  # should not raise


class _InvalidTag(DATA):
    def validate(self):
        return ["field X is required"]


def test_validate_or_raise_raises_validation_error():
    tag = _InvalidTag(code_tag="TODO", comment="x")
    with pytest.raises(ValidationError):
        tag.validate_or_raise()


# ---------------------------------------------------------------------------
# DATA.terminal_link
# ---------------------------------------------------------------------------


def test_terminal_link_with_offsets():
    tag = DATA(code_tag="TODO", comment="x", file_path="src/foo.py", offsets=(4, 0, 4, 30))
    link = tag.terminal_link()
    assert "src/foo.py" in link
    assert ":5:" in link  # start_line+1 = 5


def test_terminal_link_file_path_only():
    tag = DATA(code_tag="TODO", comment="x", file_path="src/bar.py")
    link = tag.terminal_link()
    assert "src/bar.py" in link
    assert ":0" in link


def test_terminal_link_no_path():
    tag = DATA(code_tag="TODO", comment="x")
    assert tag.terminal_link() == ""


# ---------------------------------------------------------------------------
# DATA.to_flat_dict
# ---------------------------------------------------------------------------


def test_to_flat_dict_merges_data_and_custom_fields():
    tag = DATA(
        code_tag="TODO",
        comment="x",
        data_fields={"priority": "high"},
        custom_fields={"ticket": "JIRA-1"},
    )
    flat = tag.to_flat_dict()
    assert flat["priority"] == "high"
    assert flat["ticket"] == "JIRA-1"


def test_to_flat_dict_include_comment_and_tag():
    tag = DATA(code_tag="BUG", comment="broken", data_fields={"priority": "low"})
    flat = tag.to_flat_dict(include_comment_and_tag=True)
    assert flat["comment"] == "broken"
    assert flat["code_tag"] == "BUG"


def test_to_flat_dict_raises_on_doubles():
    tag = DATA(
        code_tag="TODO",
        comment="x",
        data_fields={"priority": "high"},
        custom_fields={"priority": "low"},
    )
    with pytest.raises(DataTagError):
        tag.to_flat_dict(raise_on_doubles=True)


def test_to_flat_dict_no_raise_on_doubles_when_disabled():
    tag = DATA(
        code_tag="TODO",
        comment="x",
        data_fields={"priority": "high"},
        custom_fields={"priority": "low"},
    )
    flat = tag.to_flat_dict(raise_on_doubles=False)
    # custom_fields overwrites data_fields key
    assert "priority" in flat


def test_to_flat_dict_empty_fields():
    tag = DATA(code_tag="TODO", comment="x")
    flat = tag.to_flat_dict()
    assert flat == {}


# ---------------------------------------------------------------------------
# DATA.as_data_comment – edge cases
# ---------------------------------------------------------------------------
