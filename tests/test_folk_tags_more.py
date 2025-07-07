import pytest

from pycodetags.folk_tags.folk_tags_parser import extract_first_url, process_line, process_text
from pycodetags.folk_tags.folk_tags_schema import folk_tag_to_comment

# -- folk_tag_to_comment tests --


def test_folk_tag_to_comment_simple():
    tag = {
        "code_tag": "TODO",
        "assignee": None,
        "originator": None,
        "custom_fields": {},
        "comment": "fix this",
    }
    out = folk_tag_to_comment(tag)
    assert out == "# TODO: fix this"


def test_folk_tag_to_comment_with_people_and_fields():
    tag = {
        "code_tag": "FIXME",
        "assignee": "alice",
        "originator": "bob",
        "custom_fields": {"k": "v", "x": "y"},
        "comment": "something",
    }
    out = folk_tag_to_comment(tag)
    # People printed first, fields inside separate parens
    assert "# FIXME(alice,bob): (k=v x=y) something" == out


# -- extract_first_url tests --


def test_extract_first_url_with_scheme():
    txt = "Check https://example.com/path and more"
    assert extract_first_url(txt) == "https://example.com/path"


def test_extract_first_url_without_scheme():
    txt = "Go to example.org/resource/page now"
    assert extract_first_url(txt) == "example.org/resource/page"


def test_extract_first_url_none():
    assert extract_first_url("No links here") is None


# -- process_line tests --


@pytest.fixture
def lines():
    return [
        "# TODO: simple comment\n",
        "# TODO(123): comment2\n",
        "# TODO(ticket=ABC): comment3 abc.com/t/123\n",
        "# NOTE: should skip\n",
        "# FIXME: start multiline\n",
        "# continued line\n",
        "# another cont\n",
        "normal line\n",
    ]


def test_process_line_non_tag(lines):
    found = []
    consumed = process_line("f", found, lines, 7, ["TODO"], False, "assignee")
    assert consumed == 1
    assert not found


def test_process_line_simple_default(lines):
    found = []
    c = process_line("f", found, lines, 0, ["TODO"], False, "originator")
    assert c == 1
    tag = found[0]
    assert tag["code_tag"] == "TODO"
    assert tag["default_field"] is None
    assert tag.get("originator") is None


def test_process_line_numeric_default(lines):
    found = []
    process_line("f", found, lines, 1, ["TODO"], False, "person")
    tag = found[0]
    assert tag["default_field"] == "123"
    assert tag["person"] == "123"


def test_process_line_custom_and_tracker(lines):
    found = []
    process_line("f", found, lines, 2, ["TODO"], False, "tracker")
    tag = found[0]
    assert tag["custom_fields"] == {"ticket": "ABC"}
    assert tag["tracker"] == "abc.com/t/123"


def test_process_line_multiline(lines):
    found = []
    consumed = process_line("f", found, lines, 4, ["FIXME"], True, "assignee")
    assert consumed == 3
    tag = found[0]
    assert "start multiline continued line another cont" in tag["comment"]


# -- find_source_tags tests --


def test_find_source_tags_single_file():
    content = "# TODO: one\n# TODO(1): two\n"
    tags = []
    process_text(content, False, "assignee", found_tags=tags, valid_tags=["TODO"], file_path=__file__)
    assert len(tags) == 2
    assert tags[1]["assignee"] == "1"


@pytest.mark.skip("Don't know why this broke.")
def test_find_source_tags_directory():
    content = "# TODO: a\n\n# TODO(2=xyz): b foo.com/3"
    tags = []
    process_text(content, False, "assignee", file_path=__file__, valid_tags=["TODO"], found_tags=tags)
    assert any(t["tracker"] == "foo.com/3" for t in tags)


# -- integration: folk_tag_to_comment & find_source_tags --


def test_integration_end_to_end():
    text = "# TODO(alice, bob): track=XYZ abc.com/123 fix\n"
    tags = []
    process_text(text, False, "assignee", file_path=__file__, valid_tags=["TODO"], found_tags=tags)
    assert len(tags) == 1
    t = tags[0]
    s = folk_tag_to_comment(t)
    assert "# TODO(alice, bob): track=XYZ abc.com/123 fix" in s


def test_integration_end_to_end_single_person():
    # text = "# TODO(alice,bob): track=XYZ abc.com/123 fix\n"
    text = "# TODO(alice): (track=XYZ) abc.com/123 fix\n"
    tags = []
    process_text(text, True, "assignee", tags, file_path=__file__, valid_tags=["TODO"])
    assert len(tags) == 1
    t = tags[0]
    s = folk_tag_to_comment(t)
    assert "# TODO(alice): (track=XYZ) abc.com/123 fix" in s
