"""Identity contracts for parent issues, local IDs, tracker links, and persisted counters."""

import json
from dataclasses import replace

import pytest

from pycodetags.data_tags.data_tags_classes import DATA
from pycodetags.data_tags.identity import content_identity, content_identity_for_data, resolve_identity
from pycodetags.exceptions import DataTagError
from pycodetags.identity_counter import COUNTER_FILENAME, IdCounter
from pycodetags.pure_data_schema import PureDataSchema


@pytest.mark.parametrize("field_set", ["data_fields", "custom_fields"])
def test_parent_issue_is_not_tracker_identity(field_set):
    tag = DATA(code_tag="TODO", comment="retry uploads", **{field_set: {"issue": "100"}})
    assert resolve_identity(tag)[0] == "content"
    assert resolve_identity(replace(tag, tag_id="17")) == ("id", "17")


@pytest.mark.parametrize("field_set", ["data_fields", "custom_fields"])
def test_local_id_identifies_tag_even_with_shared_tracker_and_parent(field_set):
    url = "https://github.com/acme/repo/issues/101"
    tag = DATA(code_tag="TODO", comment="retry", tag_id="17", **{field_set: {"issue": "100", "tracker": url}})
    assert resolve_identity(tag) == ("id", "17")


def test_changing_parent_preserves_content_identity_even_with_old_schema():
    schema = dict(PureDataSchema, identity_fields=["issue"])
    first = DATA(code_tag="TODO", comment="retry", data_fields={"issue": "100"})
    second = replace(first, data_fields={"issue": "200"})
    assert content_identity_for_data(first, schema) == content_identity_for_data(second, schema)
    raw = {"code_tag": "TODO", "comment": "retry", "fields": {"data_fields": {"issue": "300"}}}
    assert content_identity(raw, schema) == content_identity_for_data(first, schema)


def test_local_identity_survives_title_and_location_changes():
    first = DATA(code_tag="TODO", comment="retry", tag_id="17", file_path="a.py")
    second = replace(first, comment="retry uploads", file_path="b.py")
    assert resolve_identity(first) == resolve_identity(second) == ("id", "17")


def test_unidentified_tags_have_content_hashes_not_unique_primary_keys():
    first = DATA(code_tag="TODO", comment="retry", file_path="a.py")
    second = replace(first, file_path="b.py")
    assert resolve_identity(first) == resolve_identity(second)
    assert resolve_identity(replace(first, comment="different")) != resolve_identity(first)


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"version": 2, "next_id": 1, "allocated": {}},
        {"version": 1, "next_id": 0, "allocated": {}},
        {"version": 1, "next_id": True, "allocated": {}},
        {"version": 1, "next_id": 1, "allocated": []},
        {"version": 1, "next_id": 1, "allocated": {"01": "hash"}},
        {"version": 1, "next_id": 1, "allocated": {"x": "hash"}},
        {"version": 1, "next_id": 1, "allocated": {"1": None}},
    ],
)
def test_invalid_counter_structure_is_rejected(tmp_path, payload):
    path = tmp_path / COUNTER_FILENAME
    path.write_text(json.dumps(payload), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(DataTagError):
        IdCounter.load(tmp_path)
    assert path.read_bytes() == before


def test_counter_reconciles_stale_next_id(tmp_path):
    path = tmp_path / COUNTER_FILENAME
    path.write_text(json.dumps({"version": 1, "next_id": 1, "allocated": {"42": "hash"}}), encoding="utf-8")
    assert IdCounter.load(tmp_path).allocate("another") == "43"


def test_existing_id_content_can_change_without_changing_id(tmp_path):
    counter = IdCounter(path=tmp_path / COUNTER_FILENAME)
    counter.record_existing("17", "old")
    counter.record_existing("17", "new")
    counter.save()
    loaded = IdCounter.load(tmp_path)
    assert loaded.allocated == {"17": "new"}
    assert loaded.allocate("next") == "18"


@pytest.mark.parametrize("tag_id", ["0", "-1", "01", "abc", "1.0", "١", ""])
def test_invalid_source_ids_cannot_be_reserved(tmp_path, tag_id):
    counter = IdCounter(path=tmp_path / COUNTER_FILENAME)
    with pytest.raises(DataTagError, match="Invalid local id"):
        counter.record_existing(tag_id, "hash")
    assert counter.known_ids == set()
