# -------------------- Unit Tests --------------------

import pytest

from pycodetags import DataTag
from pycodetags.data_tags.data_tags_methods import initialize_fields_from_schema
from pycodetags.data_tags.data_tags_schema import FieldInfo


@pytest.fixture
def example_context():
    tag = {
        "file_path": "src/auth.py",
        "comment": "Refactor login logic",
        "fields": {
            "data_fields": {
                "priority": "",
                "assignee": None,
            }
        },
    }
    meta = {
        "git_user": "matthew",
        "git_blame": "alice",
        "current_date": "2025-07-12",
    }
    field_infos = {
        "assignee": {
            "value_on_new": "meta.git_blame || meta.git_user",
            "value_on_blank": "'unassigned'",
            "value_on_delete": "'archived'",
        },
        "priority": {
            "value_on_new": "'medium'",
            "value_on_blank": "'medium'",
            "value_on_delete": "'cleared'",
        },
    }
    return tag, meta, field_infos


def test_initialize_blank_and_new_fields(example_context):
    tag, meta, field_infos = example_context

    updated_fields = initialize_fields_from_schema(tag, meta, field_infos)

    assert updated_fields["assignee"] == "unassigned"
    assert updated_fields["priority"] == "medium"


def test_blank_field_fallback():
    tag: DataTag = {"fields": {"data_fields": {"priority": ""}}}

    meta = {}
    field_infos = {"priority": {"value_on_blank": "'medium'"}}
    updated_fields = initialize_fields_from_schema(tag, meta, field_infos)
    assert updated_fields["priority"] == "medium"


def test_no_expr_no_change():
    tag: DataTag = {"fields": {"data_fields": {"assignee": "bob"}}}
    meta = {}
    field_infos: dict[str, FieldInfo] = {"assignee": {"value_on_new": "meta.git_user"}}
    updated_fields = initialize_fields_from_schema(tag, meta, field_infos)
    assert updated_fields["assignee"] == "bob"


def test_error_on_invalid_expression():
    tag: DataTag = {"fields": {"data_fields": {"assignee": None}}}
    meta = {"git_user": "matthew"}
    field_infos = {"assignee": {"value_on_new": "meta.git_user.broken.property"}}
    updated = initialize_fields_from_schema(tag, meta, field_infos)
    assert updated["assignee"] is None
