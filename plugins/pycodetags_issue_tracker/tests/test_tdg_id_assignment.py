"""Phase 4: the ``id`` command assigning ids to TDG-format tags (spec/id_and_tdg.md §2.1, §4.4).

These tests need the TDG schema active, which is gated on ``active_schemas`` containing ``TDG``. We set
a project-local config (and reset the singleton) so the TDG parser fires.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pycodetags import id_command
from pycodetags.app_config.config import CodeTagsConfig
from pycodetags.common_interfaces import list_available_schemas
from pycodetags.data_tags import convert_data_tag_to_data_object
from pycodetags.data_tags.data_tags_parsers import iterate_comments_from_file
from pycodetags.identity_counter import IdCounter


@pytest.fixture()
def tdg_project(tmp_path: Path):
    """A tmp project whose config activates the TDG schema; resets the config singleton after."""
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pycodetags]\nactive_schemas = ["TDG"]\n', encoding="utf-8"
    )
    previous = CodeTagsConfig._instance
    CodeTagsConfig.set_instance(CodeTagsConfig(pyproject_path=str(tmp_path / "pyproject.toml")))
    try:
        yield tmp_path
    finally:
        CodeTagsConfig.set_instance(previous)


def _tdg_schema():
    return next(s for s in list_available_schemas() if s.get("name") == "TDG")


def test_id_written_into_tdg_property_line(tdg_project: Path):
    f = tdg_project / "sample.py"
    f.write_text(
        "def f():\n"
        "    # TODO: Implement the TDG feature\n"
        "    # category=core estimate=30m\n"
        "    # The body of the issue\n"
        "    pass\n",
        encoding="utf-8",
    )

    _code, result = id_command.run([str(f)], counter_root=tdg_project, writer=lambda _m: None)

    assert result.assigned == 1
    text = f.read_text(encoding="utf-8")
    # id is written in TDG form (id=N on the property line), NOT converted to PEP-350 <...>.
    assert "id=1" in text
    assert "<" not in text  # never became a PEP-350 field block
    # Title and body survive.
    assert "# TODO: Implement the TDG feature" in text
    assert "The body of the issue" in text


def test_tdg_id_roundtrips_back_into_data_fields(tdg_project: Path):
    f = tdg_project / "sample.py"
    f.write_text(
        "# TODO: Round trip me\n# category=core estimate=2h\n# body line\n",
        encoding="utf-8",
    )

    id_command.run([str(f)], counter_root=tdg_project, writer=lambda _m: None)

    schema = _tdg_schema()
    raw = list(iterate_comments_from_file(str(f), schemas=[schema], include_folk_tags=False))
    assert len(raw) == 1
    tag = convert_data_tag_to_data_object(raw[0], schema)
    merged = {**(tag.data_fields or {}), **(tag.custom_fields or {})}
    assert merged.get("id") == "1"
    assert merged.get("category") == "core"
    assert merged.get("estimate") == "2h"
    assert tag.body == "body line"


def test_tdg_idempotent_and_counter_persisted(tdg_project: Path):
    f = tdg_project / "sample.py"
    f.write_text("# TODO: Only once\n# category=core\n", encoding="utf-8")

    id_command.run([str(f)], counter_root=tdg_project, writer=lambda _m: None)
    after_first = f.read_text(encoding="utf-8")

    _code, result = id_command.run([str(f)], counter_root=tdg_project, writer=lambda _m: None)
    assert result.assigned == 0
    assert result.skipped_have_id == 1
    assert f.read_text(encoding="utf-8") == after_first

    counter = IdCounter.load(tdg_project)
    assert counter.known_ids == {"1"}
    assert counter.next_id == 2


def test_tdg_tag_with_issue_is_skipped(tdg_project: Path):
    f = tdg_project / "sample.py"
    f.write_text("# TODO: tracked already\n# issue=99 category=core\n", encoding="utf-8")

    _code, result = id_command.run([str(f)], counter_root=tdg_project, writer=lambda _m: None)

    assert result.assigned == 0
    assert result.skipped_have_issue == 1
    assert "id=" not in f.read_text(encoding="utf-8")
