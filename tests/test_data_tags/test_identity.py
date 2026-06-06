"""Tests for content/local/tracker identity (spec/id_and_tdg.md Part 1)."""

from __future__ import annotations

from pycodetags.data_tags.data_tags_classes import DATA
from pycodetags.data_tags.data_tags_schema import DataTagSchema
from pycodetags.data_tags.identity import content_identity, content_identity_for_data, resolve_identity
from pycodetags.identity_counter import IdCounter


def _schema(identity_fields=None) -> DataTagSchema:
    return {
        "name": "TEST",
        "matching_tags": ["TODO"],
        "default_fields": {},
        "data_fields": {"originator": "str", "origination_date": "date", "priority": "str", "issue": "int"},
        "data_field_aliases": {},
        "field_infos": {},
        "identity_fields": identity_fields or [],
    }


def _tag(comment="do a thing", code_tag="TODO", data_fields=None, custom_fields=None):
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


# --- content_identity (DataTag) ---


def test_content_identity_is_stable_for_same_input():
    schema = _schema()
    a = content_identity(_tag(), schema)
    b = content_identity(_tag(), schema)
    assert a == b
    assert len(a) == 12


def test_content_identity_changes_with_comment():
    schema = _schema()
    assert content_identity(_tag(comment="one"), schema) != content_identity(_tag(comment="two"), schema)


def test_content_identity_changes_with_code_tag():
    schema = _schema()
    assert content_identity(_tag(code_tag="TODO"), schema) != content_identity(_tag(code_tag="FIXME"), schema)


def test_content_identity_ignores_non_identity_fields():
    """Priority is not in identity_fields, so changing it must not change identity."""
    schema = _schema(identity_fields=["originator"])
    a = content_identity(_tag(data_fields={"originator": "matth", "priority": "high"}), schema)
    b = content_identity(_tag(data_fields={"originator": "matth", "priority": "low"}), schema)
    assert a == b


def test_content_identity_uses_identity_fields():
    schema = _schema(identity_fields=["originator"])
    a = content_identity(_tag(data_fields={"originator": "matth"}), schema)
    b = content_identity(_tag(data_fields={"originator": "alice"}), schema)
    assert a != b


def test_content_identity_blank_identity_field_is_stable():
    """A missing identity field must hash the same as an explicitly-blank one."""
    schema = _schema(identity_fields=["originator"])
    a = content_identity(_tag(data_fields={}), schema)
    b = content_identity(_tag(data_fields={"originator": ""}), schema)
    assert a == b


def test_content_identity_whitespace_normalized():
    schema = _schema()
    assert content_identity(_tag(comment="a  b"), schema) == content_identity(_tag(comment="a b"), schema)


def test_content_identity_reads_from_custom_fields_fallback():
    schema = _schema(identity_fields=["originator"])
    from_data = content_identity(_tag(data_fields={"originator": "matth"}), schema)
    from_custom = content_identity(_tag(custom_fields={"originator": "matth"}), schema)
    assert from_data == from_custom


# --- content_identity_for_data (DATA object) ---


def test_content_identity_for_data_matches_dict_version():
    schema = _schema(identity_fields=["originator"])
    tag = DATA(code_tag="TODO", comment="do a thing", data_fields={"originator": "matth"})
    expected = content_identity(_tag(data_fields={"originator": "matth"}), schema)
    assert content_identity_for_data(tag, schema) == expected


def test_data_content_identity_method():
    schema = _schema()
    tag = DATA(code_tag="TODO", comment="x")
    assert tag.content_identity(schema) == content_identity_for_data(tag, schema)


# --- resolve_identity ---


def test_resolve_identity_prefers_tracker():
    schema = _schema()
    tag = DATA(code_tag="TODO", comment="x", tag_id="5", data_fields={"issue": "123"})
    assert resolve_identity(tag, schema) == ("tracker", "123")


def test_resolve_identity_falls_back_to_local_id():
    schema = _schema()
    tag = DATA(code_tag="TODO", comment="x", tag_id="5")
    assert resolve_identity(tag, schema) == ("id", "5")


def test_resolve_identity_falls_back_to_content():
    schema = _schema()
    tag = DATA(code_tag="TODO", comment="x")
    kind, value = resolve_identity(tag, schema)
    assert kind == "content"
    assert value == content_identity_for_data(tag, schema)


def test_resolve_identity_blank_fields_skipped():
    schema = _schema()
    tag = DATA(code_tag="TODO", comment="x", tag_id="  ", data_fields={"issue": ""})
    kind, _ = resolve_identity(tag, schema)
    assert kind == "content"


# --- IdCounter ---


def test_id_counter_allocate_increments(tmp_path):
    c = IdCounter(path=tmp_path / ".pycodetags_ids")
    assert c.allocate("aaa") == "1"
    assert c.allocate("bbb") == "2"
    assert c.next_id == 3


def test_id_counter_save_and_load_round_trip(tmp_path):
    path = tmp_path / ".pycodetags_ids"
    c = IdCounter(path=path)
    c.allocate("aaa")
    c.allocate("bbb")
    c.save()

    loaded = IdCounter.load(root=tmp_path)
    assert loaded.next_id == 3
    assert loaded.known_ids == {"1", "2"}
    assert loaded.allocated["1"] == "aaa"


def test_id_counter_load_missing_is_empty(tmp_path):
    loaded = IdCounter.load(root=tmp_path)
    assert loaded.next_id == 1
    assert loaded.known_ids == set()


def test_id_counter_reconciles_next_id_from_existing(tmp_path):
    c = IdCounter(path=tmp_path / ".pycodetags_ids")
    c.record_existing("42", "deadbeef")
    assert c.next_id == 43
    assert c.allocate("new") == "43"


def test_id_counter_save_is_atomic_and_sorted(tmp_path):
    path = tmp_path / ".pycodetags_ids"
    c = IdCounter(path=path)
    for i in range(12):
        c.allocate(f"content{i}")
    c.save()
    assert path.is_file()
    assert not path.with_suffix(path.suffix + ".tmp").exists()
    # numeric-aware ordering: "2" should appear before "10"
    text = path.read_text(encoding="utf-8")
    assert text.index('"2"') < text.index('"10"')
