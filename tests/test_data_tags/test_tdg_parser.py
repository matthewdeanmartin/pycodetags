"""Both explicit schemas implement the same narrative and metadata contract."""

from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pycodetags import DATA, dumps, loads, loads_all
from pycodetags.exceptions import DataTagParseError


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
@pytest.mark.parametrize(
    "body",
    [
        "",
        "one line",
        "line one\n\nline two",
        "\nleading blank",
        "trailing blank\n",
        "  indentation  ",
        "TODO: literal anchor",
        "issue=123",
        "prefix <unclosed ' markup",
        "\\literal",
        "<issue=123>",
    ],
)
def test_title_body_round_trip(schema, body):
    tag = DATA(code_tag="TODO", title="A title", body=body, tag_id="17", data_fields={"issue": "100"})
    recovered = loads(dumps(tag, schema=schema), schema=schema)
    assert recovered.title == recovered.comment == "A title"
    assert recovered.body == body
    assert recovered.tag_id == "17"
    assert recovered.data_fields["issue"] == "100"
    assert "title" not in recovered.data_fields and "body" not in recovered.data_fields


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
@pytest.mark.parametrize(
    "value",
    [
        "two words",
        "both \"double\" and 'single' quotes",
        "back\\slash",
        "",
        "0",
        "False",
        "a > b < c",
        "first\nsecond",
        "#hashtag",
        "https://github.com/acme/repo/issues/101",
    ],
)
def test_metadata_round_trip(schema, value):
    tag = DATA(code_tag="TODO", title="title", custom_fields={"detail": value})
    recovered = loads(dumps(tag, schema=schema), schema=schema)
    assert recovered.custom_fields["detail"] == value


def test_tdg_properties_are_not_body():
    tag = loads('# TODO: title\n# category="two words" issue=100 id=17\n# Description', schema="TDG")
    assert tag.title == "title"
    assert tag.body == "Description"
    assert tag.data_fields == {"category": "two words", "issue": "100"}
    assert tag.tag_id == "17"


def test_pep350_multiline_metadata_is_not_body():
    source = '# TODO: title\n# Body one\n#\n# Body two\n# <issue=100\n# category="two words"\n# id=17>'
    tag = loads(source, schema="PEP350")
    assert tag.body == "Body one\n\nBody two"
    assert tag.title == "title"
    assert tag.tag_id == "17"
    assert tag.data_fields == {"issue": "100", "category": "two words"}


def test_pep350_positional_author_date_can_be_rendered_as_tdg():
    tag = loads("# TODO: title <alice 2026-09-10 issue=100>", schema="PEP350")
    tdg = loads(dumps(tag, schema="TDG"), schema="TDG")
    assert tdg.data_fields == {"author": "alice", "origination_date": "2026-09-10", "issue": "100"}


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_long_title_is_never_wrapped(schema):
    title = "long title " * 30
    tag = loads(dumps(DATA(code_tag="TODO", title=title.rstrip()), schema=schema), schema=schema)
    assert tag.title == title.rstrip()
    assert tag.body == ""


def test_formats_represent_equivalent_records():
    tdg = loads("# TODO: title\n# issue=100 id=17\n# body", schema="TDG")
    pep = loads("# TODO: title\n# body\n# <issue=100 id=17>", schema="PEP350")
    assert (tdg.title, tdg.body, tdg.tag_id, tdg.data_fields) == (pep.title, pep.body, pep.tag_id, pep.data_fields)


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_multiple_tags_are_collected_once_in_order(schema):
    records = [DATA(code_tag="TODO", title="first"), DATA(code_tag="BUG", title="second", body="description")]
    source = "\n".join(dumps(tag, schema=schema) for tag in records)
    tags = loads_all(source, schema=schema)
    assert [tag.title for tag in tags] == ["first", "second"]
    assert [tag.body for tag in tags] == ["", "description"]


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_newly_parsed_tags_have_no_allocated_identity(schema):
    tag = loads(dumps(DATA(code_tag="TODO", title="title"), schema=schema), schema=schema)
    assert tag.tag_id is None


@pytest.mark.parametrize(
    "properties", ["issue=", 'issue="unterminated', "issue=1 issue=2", "cat=a category=b", "body=metadata"]
)
@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_invalid_metadata_is_rejected(schema, properties):
    source = "# TODO: title\n# " + properties if schema == "TDG" else "# TODO: title\n# <" + properties + ">"
    with pytest.raises(DataTagParseError):
        loads(source, schema=schema)


def test_body_prose_with_assignment_stays_body():
    tag = loads("# TODO: title\n# Use mode=fast when testing", schema="TDG")
    assert tag.body == "Use mode=fast when testing"
    assert tag.data_fields == {}


@given(st.text(alphabet=st.characters(blacklist_categories=("Cs", "Cc")), max_size=80))
def test_quoted_custom_values_survive_both_formats(value):
    for schema in ("TDG", "PEP350"):
        tag = DATA(code_tag="TODO", title="title", custom_fields={"detail": value})
        assert loads(dumps(tag, schema=schema), schema=schema).custom_fields["detail"] == value


def test_content_identity_tracks_canonical_title_edits():
    tag = loads("# TODO: old", schema="TDG")
    assert tag.content_identity(tag.schema) != replace(tag, title="new").content_identity(tag.schema)


@pytest.mark.parametrize("title", ["Use <alice>", "Compare a < b > c", r"Keep \path and <brackets>"])
@pytest.mark.parametrize("body", ["", "body"])
def test_literal_pep_title_brackets_round_trip(title, body):
    tag = DATA(code_tag="TODO", title=title, body=body)
    parsed = loads(dumps(tag, schema="PEP350"), schema="PEP350")
    assert (parsed.title, parsed.body) == (title, body)
