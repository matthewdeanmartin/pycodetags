"""Tests for pycodetags.filters – JMESPath-based filtering of DATA tags."""

from __future__ import annotations

import pytest

from pycodetags.data_tags.data_tags_classes import DATA
from pycodetags.filters import InvalidJMESPathFilter, compile_jmes_filter, filter_data_by_expression


def make_tag(code_tag="TODO", comment="x", **data_fields) -> DATA:
    return DATA(code_tag=code_tag, comment=comment, data_fields=data_fields or None)


# ---------------------------------------------------------------------------
# compile_jmes_filter
# ---------------------------------------------------------------------------


def test_compile_valid_expression_returns_callable():
    pred = compile_jmes_filter("priority")
    assert callable(pred)


def test_compile_invalid_expression_raises():
    with pytest.raises(InvalidJMESPathFilter):
        compile_jmes_filter("[[invalid")


def test_compiled_predicate_matches_truthy_field():
    pred = compile_jmes_filter("priority")
    assert pred({"priority": "high"}) is True


def test_compiled_predicate_returns_false_for_null():
    pred = compile_jmes_filter("priority")
    assert pred({"priority": None}) is False


def test_compiled_predicate_returns_false_for_missing_key():
    pred = compile_jmes_filter("priority")
    assert pred({}) is False


def test_compiled_predicate_equality_check():
    pred = compile_jmes_filter("priority == 'high'")
    assert pred({"priority": "high"}) is True
    assert pred({"priority": "low"}) is False


# ---------------------------------------------------------------------------
# filter_data_by_expression
# ---------------------------------------------------------------------------


def test_filter_by_field_presence():
    tags = [
        make_tag(priority="high"),
        make_tag(),  # no data_fields, no priority key
    ]
    result = filter_data_by_expression(tags, "priority")
    assert len(result) == 1
    assert result[0].data_fields is not None
    assert result[0].data_fields.get("priority") == "high"


def test_filter_by_field_value():
    tags = [
        make_tag(status="open"),
        make_tag(status="closed"),
        make_tag(status="open"),
    ]
    result = filter_data_by_expression(tags, "status == 'open'")
    assert len(result) == 2


def test_filter_returns_all_when_expression_is_truthy_for_all():
    tags = [make_tag(priority="high"), make_tag(priority="low")]
    result = filter_data_by_expression(tags, "priority")
    assert len(result) == 2


def test_filter_returns_empty_when_nothing_matches():
    tags = [make_tag(priority="low"), make_tag(priority="medium")]
    result = filter_data_by_expression(tags, "priority == 'high'")
    assert result == []


def test_filter_empty_list():
    assert filter_data_by_expression([], "priority") == []


def test_filter_includes_comment_in_flat_dict():
    tags = [make_tag(code_tag="TODO", comment="urgent fix", priority="high")]
    result = filter_data_by_expression(tags, "comment == 'urgent fix'")
    assert len(result) == 1


def test_filter_by_code_tag():
    tags = [
        make_tag(code_tag="TODO"),
        make_tag(code_tag="FIXME"),
    ]
    result = filter_data_by_expression(tags, "code_tag == 'FIXME'")
    assert len(result) == 1
    assert result[0].code_tag == "FIXME"
