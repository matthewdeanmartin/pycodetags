"""The ID command uses the selected format and preserves the shared record fields."""

import pytest

from pycodetags import DATA, dumps, id_command, inspect_file, loads, loads_all
from pycodetags.identity_counter import COUNTER_FILENAME


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_id_assignment_preserves_fields_and_format(tmp_path, schema):
    path = tmp_path / "sample.py"
    original = DATA(
        code_tag="TODO", title="title", body="body\n\nmore", data_fields={"category": "two words", "issue": "100"}
    )
    path.write_text(dumps(original, schema=schema), encoding="utf-8")
    code, result = id_command.run([str(path)], schema=schema, counter_root=tmp_path)
    assert code == 0 and result.assigned == 1
    tag = loads(path.read_text(encoding="utf-8"), schema=schema)
    assert tag.tag_id == "1"
    assert tag.data_fields == {"category": "two words", "issue": "100"}
    assert tag.title == "title" and tag.body == "body\n\nmore"
    before = path.read_bytes()
    assert id_command.run([str(path)], schema=schema, counter_root=tmp_path)[1].assigned == 0
    assert path.read_bytes() == before


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_contiguous_tags_each_receive_one_id(tmp_path, schema):
    path = tmp_path / "sample.py"
    path.write_text(
        "\n".join(dumps(DATA(code_tag="TODO", title=title), schema=schema) for title in ["first", "second"]),
        encoding="utf-8",
    )
    code, result = id_command.run([str(path)], schema=schema, counter_root=tmp_path)
    assert code == 0 and result.assigned == 2
    tags = loads_all(path.read_text(encoding="utf-8"), schema=schema)
    assert [(tag.title, tag.tag_id) for tag in tags] == [("first", "1"), ("second", "2")]


@pytest.mark.parametrize("mode", [{"dry_run": True}, {"check": True}])
@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_read_only_modes_do_not_touch_source_or_counter(tmp_path, schema, mode):
    path = tmp_path / "sample.py"
    path.write_text(dumps(DATA(code_tag="TODO", title="title"), schema=schema), encoding="utf-8")
    before = path.read_bytes()
    code, result = id_command.run([str(path)], schema=schema, counter_root=tmp_path, **mode)
    assert path.read_bytes() == before
    assert not (tmp_path / COUNTER_FILENAME).exists()
    assert code == (1 if mode.get("check") else 0)


def test_tracker_link_does_not_replace_local_identity(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text("# TODO: title\n# tracker=https://github.com/acme/repo/issues/101", encoding="utf-8")
    result = id_command.run([str(path)], schema="TDG", counter_root=tmp_path)[1]
    assert result.assigned == 1
    assert inspect_file(path, schema="TDG")[0].tag_id == "1"
