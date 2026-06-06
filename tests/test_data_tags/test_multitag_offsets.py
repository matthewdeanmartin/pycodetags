"""
Per-tag offsets for multiple PEP-350 tags in one comment block (spec/id_and_tdg.md Part 7).

The record-boundary bug: contiguous ``#`` lines are one *block*, but a block can hold several tags.
Every tag must report ``offsets``/``original_text`` describing *only itself*, otherwise mutating one
tag (e.g. the ``id`` command) clobbers its siblings.

The acceptance property (7.3.4): mutating tag *k* in a block leaves every other tag byte-identical.
"""

from __future__ import annotations

from pathlib import Path

from pycodetags import mutator
from pycodetags.data_tags.data_tags_classes import DATA
from pycodetags.data_tags.data_tags_methods import convert_data_tag_to_data_object
from pycodetags.data_tags.data_tags_parsers import iterate_comments
from pycodetags.pure_data_schema import PureDataSchema


def _parse(src: str) -> list[dict]:
    return list(iterate_comments(src, None, [PureDataSchema], include_folk_tags=False))


def _slice(src: str, offsets: tuple[int, int, int, int]) -> str:
    """Reconstruct the substring the offsets point at, the same way the mutator does."""
    start_line, start_char, end_line, end_char = offsets
    lines = src.splitlines(True)
    if start_line == end_line:
        return lines[start_line][start_char:end_char]
    first = lines[start_line][start_char:]
    middle = "".join(lines[start_line + 1 : end_line])
    last = lines[end_line][:end_char]
    return first + middle + last


# --------------------------------------------------------------------------------------------------
# Each tag gets its own offsets and original_text (not the whole block).
# --------------------------------------------------------------------------------------------------


def test_two_single_line_tags_get_distinct_offsets():
    src = "x = 1\n" "# FIXME: first thing <category:core>\n" "# BUG: tracked one <priority:high>\n" "y = 2\n"
    tags = _parse(src)
    assert len(tags) == 2
    by_tag = {t["code_tag"]: t for t in tags}

    # Distinct, single-line spans.
    assert by_tag["FIXME"]["offsets"] == (1, 0, 1, 36)
    assert by_tag["BUG"]["offsets"] == (2, 0, 2, 34)

    # Per-tag original_text, not the block.
    assert by_tag["FIXME"]["original_text"] == "# FIXME: first thing <category:core>"
    assert by_tag["BUG"]["original_text"] == "# BUG: tracked one <priority:high>"


def test_offsets_reconstruct_their_own_original_text():
    src = "# FIXME: first thing <category:core>\n" "# BUG: tracked one <priority:high>\n"
    for t in _parse(src):
        assert _slice(src, t["offsets"]) == t["original_text"]


def test_indented_block_offsets_account_for_indentation():
    src = "def f():\n    # TODO: a <p:1>\n    # BUG: b <p:2>\n    pass\n"
    tags = _parse(src)
    by_tag = {t["code_tag"]: t for t in tags}
    # The '#' sits at column 4 on both lines; the span runs through the closing '>'.
    assert by_tag["TODO"]["offsets"] == (1, 4, 1, 19)
    assert by_tag["BUG"]["offsets"] == (2, 4, 2, 18)
    assert by_tag["TODO"]["original_text"] == "# TODO: a <p:1>"
    assert by_tag["BUG"]["original_text"] == "# BUG: b <p:2>"


def test_three_tag_block():
    src = "# FIXME: one <category:a>\n" "# TODO: two <category:b>\n" "# BUG: three <category:c>\n"
    tags = _parse(src)
    assert [t["code_tag"] for t in tags] == ["FIXME", "TODO", "BUG"]
    for i, t in enumerate(tags):
        assert t["offsets"][0] == i  # each on its own line
        assert t["offsets"][0] == t["offsets"][2]
        assert _slice(src, t["offsets"]) == t["original_text"]


def test_single_tag_block_unchanged():
    """No regression: a lone tag's offsets still equal the block's offsets."""
    src = "# TODO: only one <priority:high>\n"
    tags = _parse(src)
    assert len(tags) == 1
    assert tags[0]["offsets"] == (0, 0, 0, 32)
    assert tags[0]["original_text"] == "# TODO: only one <priority:high>"


def test_multiline_field_block_then_second_tag():
    """A tag whose field block wraps across lines, followed by a second tag."""
    src = "# TODO: long one <p:high\n#  category:core>\n# BUG: second <s:open>\n"
    tags = _parse(src)
    by_tag = {t["code_tag"]: t for t in tags}
    # The TODO spans lines 0-1; BUG is on line 2 alone.
    assert by_tag["TODO"]["offsets"][0] == 0
    assert by_tag["TODO"]["offsets"][2] == 1
    assert by_tag["BUG"]["offsets"] == (2, 0, 2, 22)
    for t in tags:
        assert _slice(src, t["offsets"]) == t["original_text"]


# --------------------------------------------------------------------------------------------------
# Acceptance: mutating one tag in a block leaves the others byte-identical.
# --------------------------------------------------------------------------------------------------


def test_mutating_one_tag_in_block_leaves_sibling_untouched(tmp_path: Path):
    src = "# FIXME: first thing <category:core>\n" "# BUG: tracked one <priority:high>\n"
    f = tmp_path / "s.py"
    f.write_text(src, encoding="utf-8")

    raw = list(iterate_comments(src, f, [PureDataSchema], include_folk_tags=False))
    fixme = next(convert_data_tag_to_data_object(t, PureDataSchema) for t in raw if t["code_tag"] == "FIXME")

    new = DATA(code_tag="FIXME", comment="first thing", custom_fields={"category": "core", "id": "1"})
    new.offsets = fixme.offsets
    new.original_text = fixme.original_text

    mutator.apply_mutations(str(f), [(fixme, new)])

    out = f.read_text(encoding="utf-8")
    # FIXME got the id; BUG line is byte-for-byte unchanged.
    assert "# FIXME: first thing <category:core id:1>" in out
    assert "# BUG: tracked one <priority:high>" in out
    # BUG must not have been duplicated, stacked, or deleted.
    assert out.count("BUG: tracked one") == 1
    assert "id:1>id" not in out


def test_mutating_both_tags_in_block(tmp_path: Path):
    src = "# FIXME: first thing <category:core>\n" "# BUG: tracked one <priority:high>\n"
    f = tmp_path / "s.py"
    f.write_text(src, encoding="utf-8")

    raw = list(iterate_comments(src, f, [PureDataSchema], include_folk_tags=False))
    muts = []
    for t in raw:
        old = convert_data_tag_to_data_object(t, PureDataSchema)
        new = DATA(
            code_tag=old.code_tag,
            comment=old.comment,
            custom_fields={**(old.custom_fields or {}), "id": "9"},
        )
        new.offsets = old.offsets
        new.original_text = old.original_text
        muts.append((old, new))

    mutator.apply_mutations(str(f), muts)
    out = f.read_text(encoding="utf-8")
    assert out.count("id:9") == 2
    assert "# FIXME: first thing <category:core id:9>" in out
    assert "# BUG: tracked one <priority:high id:9>" in out
