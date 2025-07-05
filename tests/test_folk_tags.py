import os
import tempfile

from pycodetags.folk_code_tags import find_source_tags


def write_temp_file(content: str) -> str:
    fd, path = tempfile.mkstemp(text=True)
    with os.fdopen(fd, "w") as tmp:
        tmp.write(content)
    return path


def test_basic_todo_detection():
    path = write_temp_file("# TODO: basic task\n")
    results = find_source_tags(path)
    assert len(results) == 1
    assert results[0]["code_tag"] == "TODO"
    assert results[0]["comment"] == "basic task"


def test_non_uppercase_todo_ignored():
    path = write_temp_file("# todo: should not match\n")
    results = find_source_tags(path)
    assert len(results) == 0


def test_default_field_parsing():
    path = write_temp_file("# TODO(john): do the thing\n")
    results = find_source_tags(path)
    assert results[0]["default_field"] == "john"
    assert results[0]["comment"] == "do the thing"


def test_custom_field_parsing():
    path = write_temp_file("# TODO(owner=john, priority=high): urgent fix\n")
    results = find_source_tags(path)
    assert results[0]["custom_fields"] == {"owner": "john", "priority": "high"}
    assert results[0]["comment"] == "urgent fix"


def test_id_parsing():
    path = write_temp_file("# TODO 123: link to issue\n")
    results = find_source_tags(path)
    assert results[0]["default_field"] == "123"
    assert results[0]["comment"] == "link to issue"


def test_multiline_comment_parsing():
    content = """
# TODO: line one
# continued line
some_code()
"""
    path = write_temp_file(content)
    results = find_source_tags(path, allow_multiline=True, valid_tags=["TODO", "FIXME"])
    assert results[0]["comment"] == "line one continued line"


def test_multiline_disabled():
    content = """
# TODO: line one
# continued line
some_code()
"""
    path = write_temp_file(content)
    results = find_source_tags(path, allow_multiline=False)
    assert results[0]["comment"] == "line one"


def test_ignore_docstrings():
    content = '"""\nThis is a docstring\n TODO: inside docstring\n"""\n# TODO: real task\n'
    # A `# TODO:` in a docstring will still be found.
    path = write_temp_file(content)
    results = find_source_tags(path)
    assert len(results) == 1
    assert results[0]["comment"] == "real task"


def test_multiple_tags_in_file():
    content = """
# TODO: task one
# HACK(dev): patch here
# BUG 987: fix crash
"""
    path = write_temp_file(content)
    results = find_source_tags(path)
    assert len(results) == 3
    tags = [r["code_tag"] for r in results]
    assert set(tags) == {"TODO", "HACK", "BUG"}


def test_tag_not_in_list_is_ignored():
    path = write_temp_file("# NOTE: this is just a note\n")
    results = find_source_tags(path, valid_tags=["TODO", "FIXME"])
    assert len(results) == 0


def test_tag_not_a_tag_1():
    path = write_temp_file('# PM.set_blocked("malicious_plugin")\n')
    results = find_source_tags(path, valid_tags=["TODO"])
    assert len(results) == 0


# I guess it does look like a folk tag and the mnemonic is actually correct.
# def test_tag_not_a_tag_2():
#     path = write_temp_file('#     REQUIREMENT = namespace["REQUIREMENT"]\n')
#     results = find_source_tags(path, valid_tags=["REQUIREMENT"])
#     assert len(results) == 0


def test_tag_not_a_tag_3():
    path = write_temp_file('    "# DOTALL allows . to match newlines, VERBOSE allows comments in regex\n')
    results = find_source_tags(path, valid_tags=[])
    assert len(results) == 0
