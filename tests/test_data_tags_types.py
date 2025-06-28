# tests/test_data.py
from __future__ import  annotations
import datetime
from dataclasses import dataclass, field

from pycodetags.data_tag_types import DATA, Serializable  # adjust import path


class Dummy(Serializable):
    def __init__(self):
        self.foo = 1
        self._bar = 2
        self.when = datetime.datetime(2020, 1, 1, 12, 0)
        self.todo_meta = "should be removed"


def test_serializable_to_dict_filters_and_formats_datetime_and_private_fields():
    d = Dummy()
    dd = d.to_dict()
    assert "foo" in dd and dd["foo"] == 1
    assert "when" in dd and dd["when"] == "2020-01-01T12:00:00"
    assert "_bar" not in dd
    assert "todo_meta" not in dd


def test_data_post_init_sets_data_meta():
    data = DATA(comment="hi")
    assert data.data_meta is data


def test_call_decorator_triggers_perform_action(monkeypatch):
    performed = False

    class D(DATA):
        def _perform_action(self):
            nonlocal performed
            performed = True

    d = D(comment="test")

    @d
    def f(x):
        return x + 1

    assert f(4) == 5
    assert performed is True
    # wrapper preserves metadata
    assert hasattr(f, "todo_meta")
    assert f.todo_meta is d


def test_context_manager_enter_exit():
    data = DATA(comment="ctx")
    with data as entered:
        assert entered is data
    # __exit__ returns False to propagate exceptions
    res = DATA(comment="ctx").__exit__(None, None, None)
    assert res is False


def test_validate_returns_empty_list():
    assert not DATA(comment="x").validate()


@dataclass
class FieldData(DATA):
    a: int = 10
    b: str | None = None
    custom_fields: dict[str, str] | None = field(default_factory=lambda: {"x": "one"})
    data_fields: dict[str, str] | None = field(default_factory=lambda: {"b": "bee"})


def test_extract_data_fields_and_formatting(tmp_path):
    fd = FieldData(comment="f")
    d = fd._extract_data_fields()
    # should include a, b, comment, etc.
    assert d["a"] == "10"
    assert d["comment"] == "f"

    # TODO: No mechanism for promotion here...
    # assert d["b"] == "None" or "bee" in d.values()  # b present somehow


def test_as_data_comment_basic_and_wrapping():
    d = DATA(
        code_tag="TAG",
        comment="something",
        default_fields={"df": "Z"},
        custom_fields={"foo": "bar baz", "baz": "val"},
        data_fields={"a": "1", "c": "colon:here"},
    )
    line = d.as_data_comment()
    # must start with # TAG: something
    assert line.startswith("# TAG: something")
    # must include <Z foo:"bar baz" a:1 c:"colon:here">
    assert "<Z " in line
    assert ' foo:"bar baz" ' in line
    assert " a:1 " in line
    assert ' c:"colon:here"' in line


def test_as_data_comment_long_wraps():
    # make long comment and fields to exceed 80 chars
    many = {f"x{i}": "y" * 20 for i in range(5)}
    d = DATA(
        code_tag="T",
        comment="c" * 60,
        default_fields={"df": "D"},
        custom_fields=many,
    )
    line = d.as_data_comment()
    # contains newline after first #
    assert "\n# " in line


# @pytest.mark.asyncio
# async def test_async_not_applicable():
#     # verify no async methods break
#     d = DATA(comment="async")
#     assert await (lambda: d.validate())() == []
#
