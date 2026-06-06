"""Tests for data_tags_schema utilities and data_tags_methods conversion helpers."""

from __future__ import annotations


from pycodetags.data_tags.data_tags_methods import DataTag, convert_data_tag_to_data_object, upgrade_to_specific_schema
from pycodetags.data_tags.data_tags_schema import DataTagSchema, data_fields_as_list, merge_schemas

# ---------------------------------------------------------------------------
# merge_schemas
# ---------------------------------------------------------------------------


def _base() -> DataTagSchema:
    return {
        "name": "base",
        "matching_tags": ["TODO"],
        "default_fields": {"date": "origination_date"},
        "data_fields": {"priority": "str"},
        "data_field_aliases": {"p": "priority"},
        "field_infos": {},
        "identity_fields": [],
    }


def _override() -> DataTagSchema:
    return {
        "name": "child",
        "matching_tags": ["FIXME"],
        "default_fields": {"str": "assignee"},
        "data_fields": {"category": "str"},
        "data_field_aliases": {"c": "category"},
        "field_infos": {},
        "identity_fields": [],
    }


def test_merge_schemas_name_comes_from_override():
    merged = merge_schemas(_base(), _override())
    assert merged["name"] == "child"


def test_merge_schemas_matching_tags_are_unioned():
    merged = merge_schemas(_base(), _override())
    assert "TODO" in merged["matching_tags"]
    assert "FIXME" in merged["matching_tags"]
    assert len(merged["matching_tags"]) == 2


def test_merge_schemas_matching_tags_no_duplicates():
    b = _base()
    b["matching_tags"] = ["TODO", "FIXME"]
    o = _override()
    o["matching_tags"] = ["FIXME"]
    merged = merge_schemas(b, o)
    assert merged["matching_tags"].count("FIXME") == 1


def test_merge_schemas_data_fields_combined():
    merged = merge_schemas(_base(), _override())
    assert "priority" in merged["data_fields"]
    assert "category" in merged["data_fields"]


def test_merge_schemas_override_wins_for_same_key():
    b = _base()
    b["data_fields"]["priority"] = "int"
    o = _override()
    o["data_fields"]["priority"] = "str"
    merged = merge_schemas(b, o)
    assert merged["data_fields"]["priority"] == "str"


def test_merge_schemas_aliases_combined():
    merged = merge_schemas(_base(), _override())
    assert "p" in merged["data_field_aliases"]
    assert "c" in merged["data_field_aliases"]


def test_merge_schemas_does_not_mutate_base():
    b = _base()
    original_tags = list(b["matching_tags"])
    merge_schemas(b, _override())
    assert b["matching_tags"] == original_tags


# ---------------------------------------------------------------------------
# data_fields_as_list
# ---------------------------------------------------------------------------


def test_data_fields_as_list_returns_keys():
    schema = _base()
    result = data_fields_as_list(schema)
    assert "priority" in result
    assert isinstance(result, list)


def test_data_fields_as_list_empty_schema():
    schema = _base()
    schema["data_fields"] = {}
    assert data_fields_as_list(schema) == []


# ---------------------------------------------------------------------------
# convert_data_tag_to_data_object
# ---------------------------------------------------------------------------


def _make_tag(code_tag="TODO", comment="x", data_fields=None, custom_fields=None) -> DataTag:
    return {
        "code_tag": code_tag,
        "comment": comment,
        "fields": {
            "default_fields": {},
            "data_fields": data_fields or {},
            "custom_fields": custom_fields or {},
            "unprocessed_defaults": [],
            "identity_fields": [],
        },
    }


def test_convert_sets_code_tag_and_comment():
    schema = _base()
    obj = convert_data_tag_to_data_object(_make_tag(code_tag="BUG", comment="oops"), schema)
    assert obj.code_tag == "BUG"
    assert obj.comment == "oops"


def test_convert_populates_data_fields():
    schema = _base()
    obj = convert_data_tag_to_data_object(_make_tag(data_fields={"priority": "high"}), schema)
    assert obj.data_fields is not None
    assert obj.data_fields.get("priority") == "high"


def test_convert_moves_unknown_data_fields_to_custom():
    schema = _base()
    # 'ticket' is not in base schema's data_fields
    obj = convert_data_tag_to_data_object(_make_tag(data_fields={"ticket": "JIRA-99"}), schema)
    assert obj.custom_fields is not None
    assert "ticket" in obj.custom_fields


def test_convert_lifts_title_and_body():
    schema = _base()
    tag = _make_tag(custom_fields={"title": "My Title", "body": "Some description"})
    obj = convert_data_tag_to_data_object(tag, schema)
    assert obj.title == "My Title"
    assert obj.body == "Some description"


def test_convert_lifts_tag_id():
    schema = _base()
    tag = _make_tag(custom_fields={"id": "42"})
    obj = convert_data_tag_to_data_object(tag, schema)
    assert obj.tag_id == "42"


def test_convert_preserves_file_path_and_offsets():
    schema = _base()
    tag = _make_tag()
    tag["file_path"] = "src/module.py"
    tag["offsets"] = (10, 0, 10, 40)
    obj = convert_data_tag_to_data_object(tag, schema)
    assert obj.file_path == "src/module.py"
    assert obj.offsets == (10, 0, 10, 40)


# ---------------------------------------------------------------------------
# upgrade_to_specific_schema
# ---------------------------------------------------------------------------


def test_upgrade_separates_known_and_unknown_fields():
    schema = _base()
    tag = _make_tag(data_fields={"priority": "low", "unknown_key": "val"})
    kwargs = upgrade_to_specific_schema(tag, schema)
    assert kwargs["data_fields"]["priority"] == "low"
    assert kwargs["custom_fields"]["unknown_key"] == "val"
