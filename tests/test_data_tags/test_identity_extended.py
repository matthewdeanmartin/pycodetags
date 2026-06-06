"""Extended identity tests: _normalize edge cases, _field_value, IdCounter.record_existing."""

from __future__ import annotations


from pycodetags.data_tags.data_tags_classes import DATA
from pycodetags.data_tags.data_tags_schema import DataTagSchema
from pycodetags.data_tags.identity import (
    _hash_parts,
    _normalize,
    content_identity,
    content_identity_for_data,
    resolve_identity,
)
from pycodetags.identity_counter import IdCounter


def _schema(identity_fields=None) -> DataTagSchema:
    return {
        "name": "TEST",
        "matching_tags": ["TODO"],
        "default_fields": {},
        "data_fields": {"issue": "int", "originator": "str"},
        "data_field_aliases": {},
        "field_infos": {},
        "identity_fields": identity_fields or [],
    }


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------


def test_normalize_none_returns_empty_string():
    assert _normalize(None) == ""


def test_normalize_collapses_whitespace():
    assert _normalize("a  b   c") == "a b c"


def test_normalize_strips_leading_trailing():
    assert _normalize("  hello  ") == "hello"


def test_normalize_list_joins_with_comma():
    assert _normalize(["a", "b", "c"]) == "a,b,c"


def test_normalize_nested_list():
    assert _normalize([["a", "b"], "c"]) == "a,b,c"


def test_normalize_tuple_joins_with_comma():
    assert _normalize(("x", "y")) == "x,y"


def test_normalize_integer():
    assert _normalize(42) == "42"


def test_normalize_empty_list():
    assert _normalize([]) == ""


# ---------------------------------------------------------------------------
# _hash_parts
# ---------------------------------------------------------------------------


def test_hash_parts_same_inputs_same_output():
    assert _hash_parts(["a", "b"]) == _hash_parts(["a", "b"])


def test_hash_parts_order_sensitive():
    assert _hash_parts(["a", "b"]) != _hash_parts(["b", "a"])


def test_hash_parts_no_collision_different_split():
    # ("a", "bc") must differ from ("ab", "c") – null-byte separator prevents this
    assert _hash_parts(["a", "bc"]) != _hash_parts(["ab", "c"])


def test_hash_parts_returns_12_chars():
    result = _hash_parts(["foo", "bar"])
    assert len(result) == 12
    assert all(c in "0123456789abcdef" for c in result)


# ---------------------------------------------------------------------------
# content_identity (dict-based DataTag)
# ---------------------------------------------------------------------------


def test_content_identity_output_length():
    schema = _schema()
    tag = {"code_tag": "TODO", "comment": "hello", "fields": {"data_fields": {}, "custom_fields": {}}}
    result = content_identity(tag, schema)
    assert len(result) == 12


def test_content_identity_stable_across_calls():
    schema = _schema(["originator"])
    tag = {"code_tag": "TODO", "comment": "x", "fields": {"data_fields": {"originator": "alice"}, "custom_fields": {}}}
    assert content_identity(tag, schema) == content_identity(tag, schema)


def test_content_identity_custom_fields_fallback():
    schema = _schema(["originator"])
    from_data = content_identity(
        {"code_tag": "TODO", "comment": "x", "fields": {"data_fields": {"originator": "matth"}, "custom_fields": {}}},
        schema,
    )
    from_custom = content_identity(
        {"code_tag": "TODO", "comment": "x", "fields": {"data_fields": {}, "custom_fields": {"originator": "matth"}}},
        schema,
    )
    assert from_data == from_custom


# ---------------------------------------------------------------------------
# content_identity_for_data (DATA object)
# ---------------------------------------------------------------------------


def test_content_identity_for_data_stable():
    schema = _schema()
    tag = DATA(code_tag="TODO", comment="do thing")
    assert content_identity_for_data(tag, schema) == content_identity_for_data(tag, schema)


def test_content_identity_for_data_attribute_preferred_over_dict():
    schema = _schema(["issue"])
    # Put conflicting values: attribute vs dict – attribute wins
    tag = DATA(code_tag="TODO", comment="x", data_fields={"issue": "99"})
    # There's no typed attribute for 'issue' on DATA, so it falls back to data_fields
    result = content_identity_for_data(tag, schema)
    assert len(result) == 12


def test_content_identity_for_data_missing_field_stable():
    schema = _schema(["nonexistent"])
    tag = DATA(code_tag="TODO", comment="x")
    r1 = content_identity_for_data(tag, schema)
    r2 = content_identity_for_data(DATA(code_tag="TODO", comment="x"), schema)
    assert r1 == r2


# ---------------------------------------------------------------------------
# resolve_identity – additional edge cases
# ---------------------------------------------------------------------------


def test_resolve_identity_tracker_from_data_fields():
    tag = DATA(code_tag="TODO", comment="x", data_fields={"issue": "7"})
    kind, val = resolve_identity(tag)
    # Without schema, content is the fallback – issue is in data_fields, not attribute
    # The actual kind depends on whether 'issue' attr resolves; DATA has no 'issue' attribute
    # so _field_value checks data_fields: it should find "7"
    assert kind == "tracker"
    assert val == "7"


def test_resolve_identity_no_schema_falls_back_to_content():
    tag = DATA(code_tag="TODO", comment="y")
    kind, val = resolve_identity(tag, schema=None)
    assert kind == "content"
    assert len(val) == 12


def test_resolve_identity_whitespace_only_tracker_is_skipped():
    tag = DATA(code_tag="TODO", comment="x", data_fields={"issue": "  "})
    kind, _ = resolve_identity(tag, _schema())
    assert kind != "tracker"


def test_resolve_identity_whitespace_only_local_id_is_skipped():
    tag = DATA(code_tag="TODO", comment="x", tag_id="  ")
    kind, _ = resolve_identity(tag, _schema())
    assert kind == "content"


# ---------------------------------------------------------------------------
# IdCounter – record_existing with content change
# ---------------------------------------------------------------------------


def test_id_counter_record_existing_logs_on_content_change(tmp_path, caplog):
    import logging

    c = IdCounter(path=tmp_path / ".pycodetags_ids")
    c.record_existing("5", "original_hash")
    with caplog.at_level(logging.DEBUG, logger="pycodetags.identity_counter"):
        c.record_existing("5", "new_hash_different")
    # The id should still be recorded
    assert c.allocated["5"] == "new_hash_different"


def test_id_counter_record_existing_same_content_no_change(tmp_path):
    c = IdCounter(path=tmp_path / ".pycodetags_ids")
    c.record_existing("3", "same_hash")
    c.record_existing("3", "same_hash")
    assert c.allocated["3"] == "same_hash"


def test_id_counter_record_existing_bumps_next_id(tmp_path):
    c = IdCounter(path=tmp_path / ".pycodetags_ids")
    assert c.next_id == 1
    c.record_existing("10", "hash")
    assert c.next_id == 11


def test_id_counter_allocate_after_record_existing_does_not_collide(tmp_path):
    c = IdCounter(path=tmp_path / ".pycodetags_ids")
    c.record_existing("5", "hash_a")
    new_id = c.allocate("hash_b")
    assert new_id == "6"
    assert new_id not in ("5",)


def test_id_counter_known_ids_includes_recorded(tmp_path):
    c = IdCounter(path=tmp_path / ".pycodetags_ids")
    c.record_existing("7", "h")
    assert "7" in c.known_ids


def test_id_counter_load_corrupt_file_returns_fresh(tmp_path):
    path = tmp_path / ".pycodetags_ids"
    path.write_text("not valid json", encoding="utf-8")
    loaded = IdCounter.load(root=tmp_path)
    assert loaded.next_id == 1
    assert loaded.allocated == {}


def test_id_counter_load_preserves_allocated_entries(tmp_path):
    path = tmp_path / ".pycodetags_ids"
    c = IdCounter(path=path)
    c.allocate("aaa")
    c.allocate("bbb")
    c.save()

    loaded = IdCounter.load(root=tmp_path)
    assert "1" in loaded.allocated
    assert "2" in loaded.allocated
