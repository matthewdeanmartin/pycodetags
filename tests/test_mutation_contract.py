"""Mutation safety and preservation tests against real source files."""

import os
from dataclasses import replace

import pytest

from pycodetags import DATA, apply_mutations, delete_tags, dumps, inspect_file, loads_all, source_io, update_tags
from pycodetags.exceptions import DataTagError, DataTagParseError
from pycodetags.mutator import insert_tags, replace_with_strings


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "latin-1"])
def test_batch_preserves_encoding_newlines_body_and_surrounding_bytes(tmp_path, schema, newline, encoding):
    path = tmp_path / "source.py"
    first = DATA(code_tag="TODO", title="café", body="old", tag_id="7")
    second = DATA(code_tag="BUG", title="remove")
    prefix = "# coding: " + ("utf-8" if encoding == "utf-8-sig" else encoding) + newline + "if True:" + newline
    first_text = (newline + "\t").join(dumps(first, schema=schema).split("\n"))
    second_text = (newline + "\t").join(dumps(second, schema=schema).split("\n"))
    middle = newline + "\tpass" + newline + "\t"
    suffix = newline + "\tvalue = 'café'"  # Deliberately no final newline.
    source = prefix + "\t" + first_text + middle + second_text + suffix
    path.write_bytes(source.encode(encoding))
    old, removed = inspect_file(path, schema=schema)
    new = replace(old, title="updated", body="  indented\n\nlast  ")
    apply_mutations(path, [(removed, None), (old, new)])
    expected_tag = (newline + "\t").join(dumps(new).split("\n"))
    assert path.read_bytes() == (prefix + "\t" + expected_tag + middle + suffix).encode(encoding)
    parsed = inspect_file(path, schema=schema)[0]
    assert (parsed.body, parsed.tag_id) == (new.body, "7")


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_inline_expansion_does_not_duplicate_executable_prefix(tmp_path, schema):
    path = tmp_path / "source.py"
    path.write_bytes(
        ("if True:\n\tx = '🐍'; " + dumps(DATA(code_tag="TODO", title="old"), schema=schema) + "\n\tpass\n").encode()
    )
    old = inspect_file(path, schema=schema)[0]
    update_tags(path, [(old, replace(old, body="details\n  more"))])
    text = path.read_bytes().decode()
    assert text.count("x = '🐍';") == 1
    assert "\n\t# details\n\t#   more" in text
    compile(text, str(path), "exec")


def test_mixed_format_explicit_snapshots_share_one_batch(tmp_path):
    path = tmp_path / "mixed.py"
    source = "# TODO: first\nx = 1\n# BUG: second <>\n# ordinary\n"
    path.write_bytes(source.encode())
    tdg = inspect_file(path, schema="TDG")[0]
    pep = inspect_file(path, schema="PEP350")[0]
    apply_mutations(path, [(tdg, replace(tdg, body="longer\nbody")), (pep, None)])
    assert path.read_bytes() == b"# TODO: first\n# longer\n# body\nx = 1\n\n# ordinary\n"


@pytest.mark.parametrize("change", ["whitespace", "unrelated", "newlines"])
def test_stale_file_snapshot_fails_without_writes(tmp_path, change):
    path = tmp_path / "source.py"
    source = b"# TODO: old\n# body  text\nx = 1\n"
    path.write_bytes(source)
    tag = inspect_file(path, schema="TDG")[0]
    edited = {
        "whitespace": source.replace(b"body  ", b"body "),
        "unrelated": source.replace(b"x = 1", b"x = 2"),
        "newlines": source.replace(b"\n", b"\r\n"),
    }[change]
    path.write_bytes(edited)
    with pytest.raises(DataTagError, match="Tag mismatch"):
        delete_tags(path, [tag])
    assert path.read_bytes() == edited


@pytest.mark.parametrize(
    "offsets",
    [(-1, 0, 0, 1), (0, -1, 0, 3), (0, 0, 99, 1), (0, 0, 0, 999), (0, 5, 0, 3), (0, 0, 0, 0), (False, 0, 0, 1)],
)
def test_invalid_spans_fail_without_writes(tmp_path, offsets):
    path = tmp_path / "source.py"
    original = b"# TODO: old\n"
    path.write_bytes(original)
    tag = inspect_file(path, schema="TDG")[0]
    with pytest.raises(DataTagError, match="Invalid tag offsets"):
        delete_tags(path, [replace(tag, offsets=offsets)])
    assert path.read_bytes() == original


def test_duplicate_and_overlapping_spans_fail_without_writes(tmp_path):
    path = tmp_path / "source.py"
    original = b"# TODO: old\n# body\n"
    path.write_bytes(original)
    tag = inspect_file(path, schema="TDG")[0]
    for other in (tag, replace(tag, offsets=(1, 0, 1, 6), original_text="# body")):
        with pytest.raises(DataTagError, match="Overlapping"):
            delete_tags(path, [tag, other])
        assert path.read_bytes() == original


def test_wrong_file_and_missing_snapshot_rejected(tmp_path):
    path = tmp_path / "source.py"
    other = tmp_path / "other.py"
    path.write_bytes(b"# TODO: old\n")
    other.write_bytes(path.read_bytes())
    tag = inspect_file(path, schema="TDG")[0]
    with pytest.raises(DataTagError, match="different source"):
        delete_tags(other, [tag])
    with pytest.raises(DataTagError, match="snapshot"):
        delete_tags(path, [replace(tag, source_digest=None)])


def test_whole_batch_serializes_before_writing(tmp_path):
    path = tmp_path / "source.py"
    original = b"# TODO: first\n# BUG: second\n"
    path.write_bytes(original)
    first, second = inspect_file(path, schema="TDG")
    with pytest.raises(DataTagParseError):
        update_tags(path, [(first, replace(first, title="valid")), (second, replace(second, title="bad\ntitle"))])
    assert path.read_bytes() == original


def test_unencodable_update_does_not_touch_source(tmp_path):
    path = tmp_path / "source.py"
    original = b"# coding: latin-1\n# TODO: old\n"
    path.write_bytes(original)
    tag = inspect_file(path, schema="TDG")[0]
    with pytest.raises(UnicodeEncodeError):
        update_tags(path, [(tag, replace(tag, title="🐍"))])
    assert path.read_bytes() == original
    assert list(tmp_path.glob("*.tmp")) == []


def test_replace_failure_cleans_unique_temporary_file(tmp_path, monkeypatch):
    path = tmp_path / "source.py"
    original = b"# TODO: old\n"
    path.write_bytes(original)
    unrelated = tmp_path / "source.py.tmp"
    unrelated.write_bytes(b"someone else's file")
    tag = inspect_file(path, schema="TDG")[0]

    def fail_replace(source, destination):
        assert source != unrelated
        raise OSError("simulated failure")

    monkeypatch.setattr(source_io.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated failure"):
        delete_tags(path, [tag])
    assert path.read_bytes() == original
    assert unrelated.read_bytes() == b"someone else's file"
    assert list(tmp_path.glob(".source.py.*.tmp")) == []


def test_edit_during_serialization_is_detected(tmp_path):
    path = tmp_path / "source.py"
    path.write_bytes(b"# TODO: old\n")
    tag = inspect_file(path, schema="TDG")[0]
    edited = b"# TODO: external edit\n"

    def serialize(record):
        path.write_bytes(edited)
        return dumps(record)

    with pytest.raises(DataTagError, match="source changed"):
        apply_mutations(path, [(tag, replace(tag, title="mine"))], serializer=serialize)
    assert path.read_bytes() == edited
    assert list(tmp_path.glob(".source.py.*.tmp")) == []


def test_title_helper_preserves_body_and_identity_without_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "source.py"
    path.write_bytes(b"# TODO: old\n# id=7 issue=100\n# description\n")
    tag = inspect_file(path, schema="TDG")[0]
    replace_with_strings(path, [(tag, "new")])
    parsed = inspect_file(path, schema="TDG")[0]
    assert (parsed.title, parsed.body, parsed.tag_id, parsed.data_fields["issue"]) == ("new", "description", "7", "100")


def test_new_replacement_inherits_old_explicit_schema(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "source.py"
    path.write_bytes(b"# TODO: old\n")
    old = inspect_file(path, schema="TDG")[0]
    update_tags(path, [(old, DATA(code_tag="DONE", title="finished"))])
    assert path.read_bytes() == b"# DONE: finished\n"


def test_mixed_newlines_outside_span_are_unchanged(tmp_path):
    path = tmp_path / "source.py"
    path.write_bytes(b"x = 1\r\n# TODO: old\n# body\r\ny = 2\n")
    old = inspect_file(path, schema="TDG")[0]
    update_tags(path, [(old, replace(old, body="new\nmore"))])
    assert path.read_bytes() == b"x = 1\r\n# TODO: old\n# new\n# more\r\ny = 2\n"


def test_insert_validates_duplicates_and_preserves_input_and_eof(tmp_path):
    path = tmp_path / "source.py"
    path.write_bytes(b"\r\nx = 1")
    tag = loads_all("# TODO: new", schema="TDG")[0]
    insertions = [(3, tag, 0), (1, tag, 0)]
    original_order = list(insertions)
    insert_tags(path, insertions)
    assert insertions == original_order
    assert path.read_bytes() == b"# TODO: new\r\n\r\nx = 1\r\n# TODO: new"
    before = path.read_bytes()
    with pytest.raises(ValueError, match="Duplicate"):
        insert_tags(path, [(2, tag, 0), (2, tag, 0)])
    assert path.read_bytes() == before


def test_mode_preserved_and_empty_batch_does_not_replace(tmp_path, monkeypatch):
    path = tmp_path / "source.py"
    path.write_bytes(b"# TODO: old\n")
    mode = path.stat().st_mode
    tag = inspect_file(path, schema="TDG")[0]
    update_tags(path, [(tag, replace(tag, title="new"))])
    assert path.stat().st_mode == mode

    def unexpected(*args):
        raise AssertionError("Empty batch should not replace")

    monkeypatch.setattr(source_io.os, "replace", unexpected)
    apply_mutations(path, [])


def test_hardlinked_file_is_rejected(tmp_path):
    path = tmp_path / "source.py"
    path.write_bytes(b"# TODO: old\n")
    other = tmp_path / "linked.py"
    os.link(path, other)
    tag = inspect_file(path, schema="TDG")[0]
    with pytest.raises(DataTagError, match="single link"):
        delete_tags(path, [tag])
    assert path.read_bytes() == other.read_bytes() == b"# TODO: old\n"


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_deletion_respects_agreed_ordinary_comment_boundary(tmp_path, schema):
    path = tmp_path / "source.py"
    source = (
        "# TODO: title\n# body\n\n# ordinary\nx = 1\n"
        if schema == "TDG"
        else "# TODO: title\n# body\n# <>\n# ordinary\nx = 1\n"
    )
    path.write_bytes(source.encode())
    tag = inspect_file(path, schema=schema)[0]
    delete_tags(path, [tag])
    assert path.read_bytes().endswith(b"# ordinary\nx = 1\n")
    assert b"body" not in path.read_bytes()


def test_failed_flush_cleans_temporary_and_leaves_source(tmp_path, monkeypatch):
    path = tmp_path / "source.py"
    original = b"# TODO: old\n"
    path.write_bytes(original)
    tag = inspect_file(path, schema="TDG")[0]

    def fail_flush(descriptor):
        raise OSError("flush failed")

    monkeypatch.setattr(source_io.os, "fsync", fail_flush)
    with pytest.raises(OSError, match="flush failed"):
        delete_tags(path, [tag])
    assert path.read_bytes() == original
    assert list(tmp_path.glob(".source.py.*.tmp")) == []


def test_id_assignment_uses_one_replacement_per_file(tmp_path, monkeypatch):
    from pycodetags.id_command import run

    path = tmp_path / "source.py"
    path.write_bytes(b"# TODO: first\n# BUG: second\n")
    actual_replace = source_io.os.replace
    source_writes = []

    def count_replace(source, destination):
        if destination == path:
            source_writes.append(destination)
        return actual_replace(source, destination)

    monkeypatch.setattr(source_io.os, "replace", count_replace)
    code, result = run([str(path)], schema="TDG", counter_root=tmp_path, writer=lambda message: None)
    assert code == 0 and result.assigned == 2
    assert source_writes == [path]
    assert [tag.tag_id for tag in inspect_file(path, schema="TDG")] == ["1", "2"]
