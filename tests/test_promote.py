# tests/test_promote_fields.py

import pytest

from pycodetags.data_tags_methods import promote_fields
from pycodetags.data_tags_schema import DataTag


@pytest.fixture
def simple_schema():
    return {
        "name": "TestSchema",
        "matching_tags": [],
        "default_fields": {"str": "originator", "date": "origination_date"},
        "data_fields": {
            "originator": "str",
            "priority": "str",
        },
        "data_field_aliases": {
            "p": "priority",  # alias for testing
        },
    }


@pytest.mark.skip()
def test_promote_default_fields_to_data_fields(simple_schema):
    tag: DataTag = {
        "code_tag": "TODO",
        "comment": "Fix this",
        "fields": {
            "default_fields": {
                "originator": ["JD"],
            },
            "data_fields": {},
            "custom_fields": {},
        },
    }

    promote_fields(tag, simple_schema)

    assert "originator" in tag["fields"]["data_fields"]
    assert tag["fields"]["data_fields"]["originator"] in (["JD"], "JD")  # catdog
    assert not tag["fields"]["default_fields"] or "originator" not in tag["fields"]["default_fields"]


@pytest.mark.skip()
def test_promote_custom_fields_with_alias(simple_schema):
    tag: DataTag = {
        "code_tag": "TODO",
        "comment": "Fix with priority",
        "fields": {
            "default_fields": {},
            "data_fields": {},
            "custom_fields": {"p": "high"},
        },
    }

    promote_fields(tag, simple_schema)

    assert "priority" in tag["fields"]["data_fields"]
    assert tag["fields"]["data_fields"]["priority"] == "high"
    assert "p" not in tag["fields"]["custom_fields"]


@pytest.mark.skip()
def test_merge_conflicting_fields_list_merge(simple_schema):
    tag: DataTag = {
        "code_tag": "TODO",
        "comment": "Merge test",
        "fields": {
            "default_fields": {"originator": ["JD"]},
            "data_fields": {"originator": ["JS"]},
            "custom_fields": {},
        },
    }

    promote_fields(tag, simple_schema)

    assert tag["fields"]["data_fields"]["originator"] == ["JS", "JD"]
    assert "originator" not in tag["fields"]["default_fields"]


def test_merge_custom_and_data_field_with_alias_and_conflict(simple_schema):
    tag: DataTag = {
        "code_tag": "TODO",
        "comment": "Merge alias conflict",
        "fields": {
            "unprocessed_defaults": [],
            "default_fields": {},
            "data_fields": {"priority": "medium"},
            "custom_fields": {"p": "high"},  # alias to priority
        },
    }

    promote_fields(tag, simple_schema)

    # priority existed in both -> should be merged into list
    value = tag["fields"]["data_fields"]["priority"]
    assert isinstance(value, list)
    assert "medium" in value and "high" in value
    assert "p" not in tag["fields"]["custom_fields"]
