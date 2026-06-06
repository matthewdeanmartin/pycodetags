"""
Tests for Phase 4: the ``pycodetags id`` command and its round-trip safety.

These are core tests: they exercise PEP-350 tags only (no plugin needed), since ``PureDataSchema`` is
always active. TDG-specific id assignment lives in the plugin test suite.
"""

from __future__ import annotations

from pathlib import Path

from pycodetags import id_command, mutator
from pycodetags.data_tags import DATA, convert_data_tag_to_data_object
from pycodetags.data_tags.data_tags_parsers import iterate_comments_from_file
from pycodetags.identity_counter import COUNTER_FILENAME, IdCounter
from pycodetags.pure_data_schema import PureDataSchema


def _write(tmp_path: Path, content: str, name: str = "sample.py") -> Path:
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return f


def _parse_one(file: Path) -> DATA:
    raw = list(iterate_comments_from_file(str(file), schemas=[PureDataSchema], include_folk_tags=False))
    assert len(raw) == 1, f"expected exactly one tag, got {len(raw)}"
    return convert_data_tag_to_data_object(raw[0], PureDataSchema)


# --------------------------------------------------------------------------------------------------
# Round-trip safety (spec §2.1): parse -> assign id -> serialize -> re-parse keeps all fields.
# --------------------------------------------------------------------------------------------------


def test_pep350_roundtrip_preserves_fields_and_adds_id(tmp_path: Path):
    f = _write(tmp_path, "# TODO: Implement feature X <priority:high category:new>\n")
    original = _parse_one(f)

    id_command.run([str(f)], counter_root=tmp_path, writer=lambda _m: None)

    updated = _parse_one(f)
    # All original fields survive.
    assert updated.comment == original.comment
    assert updated.code_tag == original.code_tag
    merged = {**(updated.data_fields or {}), **(updated.custom_fields or {})}
    assert merged.get("priority") == "high"
    assert merged.get("category") == "new"
    # And an id was added.
    assert merged.get("id") == "1"
    assert updated.tag_id == "1"


def test_pep350_roundtrip_is_idempotent(tmp_path: Path):
    f = _write(tmp_path, "# TODO: do a thing <priority:low>\n")
    id_command.run([str(f)], counter_root=tmp_path, writer=lambda _m: None)
    after_first = f.read_text(encoding="utf-8")

    _code, result = id_command.run([str(f)], counter_root=tmp_path, writer=lambda _m: None)
    after_second = f.read_text(encoding="utf-8")

    assert after_first == after_second
    assert result.assigned == 0
    assert result.skipped_have_id == 1


# --------------------------------------------------------------------------------------------------
# Command behavior.
# --------------------------------------------------------------------------------------------------


def test_assigns_sequential_ids_and_writes_counter(tmp_path: Path):
    f = _write(
        tmp_path,
        "# TODO: first thing <priority:high>\n\n\n# TODO: second thing <priority:low>\n",
    )
    _code, result = id_command.run([str(f)], counter_root=tmp_path, writer=lambda _m: None)

    assert result.assigned == 2
    text = f.read_text(encoding="utf-8")
    assert "id:1" in text
    assert "id:2" in text

    counter_file = tmp_path / COUNTER_FILENAME
    assert counter_file.is_file()
    counter = IdCounter.load(tmp_path)
    assert counter.next_id == 3
    assert counter.known_ids == {"1", "2"}


def test_dry_run_writes_nothing(tmp_path: Path):
    f = _write(tmp_path, "# TODO: untouched <priority:high>\n")
    before = f.read_text(encoding="utf-8")

    messages: list[str] = []
    code, result = id_command.run([str(f)], dry_run=True, counter_root=tmp_path, writer=messages.append)

    assert code == 0
    assert result.assigned == 1
    assert f.read_text(encoding="utf-8") == before  # source untouched
    assert not (tmp_path / COUNTER_FILENAME).exists()  # counter untouched
    assert any("dry-run" in m for m in messages)


def test_check_returns_nonzero_when_missing_id(tmp_path: Path):
    f = _write(tmp_path, "# TODO: needs an id <priority:high>\n")
    before = f.read_text(encoding="utf-8")

    code, result = id_command.run([str(f)], check=True, counter_root=tmp_path, writer=lambda _m: None)

    assert code == 1
    assert result.assigned == 0
    assert f.read_text(encoding="utf-8") == before
    assert not (tmp_path / COUNTER_FILENAME).exists()


def test_check_passes_after_assignment(tmp_path: Path):
    f = _write(tmp_path, "# TODO: will get an id <priority:high>\n")
    id_command.run([str(f)], counter_root=tmp_path, writer=lambda _m: None)

    code, _result = id_command.run([str(f)], check=True, counter_root=tmp_path, writer=lambda _m: None)
    assert code == 0


def test_skips_tag_with_issue(tmp_path: Path):
    # A tracker-backed tag already has the strongest identity and must not get a local id.
    f = _write(tmp_path, "# TODO: tracked <priority:high issue=42>\n")
    _code, result = id_command.run([str(f)], counter_root=tmp_path, writer=lambda _m: None)

    assert result.assigned == 0
    assert result.skipped_have_issue == 1
    assert "id:" not in f.read_text(encoding="utf-8")
    assert "id=" not in f.read_text(encoding="utf-8")


def test_does_not_reassign_existing_id(tmp_path: Path):
    f = _write(tmp_path, "# TODO: already has one <priority:high id=7>\n")
    _code, result = id_command.run([str(f)], counter_root=tmp_path, writer=lambda _m: None)

    assert result.assigned == 0
    assert result.skipped_have_id == 1
    # Existing id is preserved exactly.
    assert "id=7" in f.read_text(encoding="utf-8") or "id:7" in f.read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------------------
# Shared-block safety: two tags in one contiguous comment block must not be mutated (would corrupt).
# --------------------------------------------------------------------------------------------------


def test_missing_path_is_skipped_gracefully(tmp_path: Path):
    code, result = id_command.run([str(tmp_path / "does_not_exist.py")], counter_root=tmp_path, writer=lambda _m: None)
    assert code == 0
    assert result.scanned == 0
    assert result.assigned == 0


# --------------------------------------------------------------------------------------------------
# In-block tags: contiguous tags now get per-tag offsets, so each is assigned independently and
# safely (spec/id_and_tdg.md Part 7). No corruption, no clobbered siblings.
# --------------------------------------------------------------------------------------------------


def test_contiguous_tags_each_get_an_id(tmp_path: Path):
    # FIXME and BUG are contiguous comment lines -> one comment block, but distinct per-tag offsets.
    content = "# FIXME: first in block <priority:high>\n# BUG: second in block <priority:low>\n"
    f = _write(tmp_path, content)

    _code, result = id_command.run([str(f)], counter_root=tmp_path, writer=lambda _m: None)

    assert result.assigned == 2
    assert result.skipped_shared_block == 0
    text = f.read_text(encoding="utf-8")
    # Both tags got an id; neither clobbered the other.
    assert "# FIXME: first in block <priority:high id:" in text
    assert "# BUG: second in block <priority:low id:" in text
    assert text.count("FIXME: first in block") == 1
    assert text.count("BUG: second in block") == 1
    assert "id:1>id" not in text and "id:2>id" not in text


def test_contiguous_tags_roundtrip_reparse(tmp_path: Path):
    content = "# FIXME: alpha <priority:high>\n# BUG: beta <priority:low>\n"
    f = _write(tmp_path, content)
    id_command.run([str(f)], counter_root=tmp_path, writer=lambda _m: None)

    # Re-parsing the mutated file yields exactly two tags, each with its id, fields intact.
    raw = list(iterate_comments_from_file(str(f), schemas=[PureDataSchema], include_folk_tags=False))
    assert len(raw) == 2
    tags = [convert_data_tag_to_data_object(r, PureDataSchema) for r in raw]
    for tag in tags:
        merged = {**(tag.data_fields or {}), **(tag.custom_fields or {})}
        assert "id" in merged
        assert "priority" in merged


def test_mixed_standalone_and_contiguous_tags(tmp_path: Path):
    content = (
        "# TODO: standalone one <priority:high>\n"
        "\n\n"
        "# FIXME: contiguous a <priority:high>\n"
        "# BUG: contiguous b <priority:low>\n"
        "\n\n"
        "# HACK: standalone two <priority:low>\n"
    )
    f = _write(tmp_path, content)

    _code, result = id_command.run([str(f)], counter_root=tmp_path, writer=lambda _m: None)

    assert result.assigned == 4  # all four tags
    assert result.skipped_shared_block == 0
    text = f.read_text(encoding="utf-8")
    # Every tag preserved exactly once and carries an id.
    for marker in ("standalone one", "contiguous a", "contiguous b", "standalone two"):
        assert text.count(marker) == 1
    assert text.count("id:") == 4


# --------------------------------------------------------------------------------------------------
# Mutator serializer hook (used by the id command for TDG; default must stay PEP-350).
# --------------------------------------------------------------------------------------------------


def test_mutator_default_serializer_is_pep350(tmp_path: Path):
    f = _write(tmp_path, "# TODO: hello <priority:high>\n")
    old = _parse_one(f)
    new = DATA(code_tag="TODO", comment="hello", custom_fields={"priority": "high", "id": "5"})
    # Reuse the parsed tag's source mapping so the mutator can locate it.
    new.offsets = old.offsets
    new.original_text = old.original_text

    mutator.apply_mutations(str(f), [(old, new)])
    assert "id:5" in f.read_text(encoding="utf-8")


def test_mutator_custom_serializer_is_used(tmp_path: Path):
    f = _write(tmp_path, "# TODO: hello <priority:high>\n")
    old = _parse_one(f)
    new = DATA(code_tag="TODO", comment="hello")
    new.offsets = old.offsets
    new.original_text = old.original_text

    mutator.apply_mutations(str(f), [(old, new)], serializer=lambda _t: "# REPLACED")
    assert "# REPLACED" in f.read_text(encoding="utf-8")
    assert "TODO" not in f.read_text(encoding="utf-8")
