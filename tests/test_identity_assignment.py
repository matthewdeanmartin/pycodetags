"""ID allocation reserves all selected source identities before writing anything."""

from pathlib import Path

import pytest

from pycodetags import id_command
from pycodetags.common_interfaces import string_to_data
from pycodetags.exceptions import DataTagError
from pycodetags.identity_counter import COUNTER_FILENAME, IdCounter
from pycodetags.pure_data_schema import PureDataSchema


def write_source(root: Path, name: str, content: str) -> Path:
    path = root / name
    path.write_text(content, encoding="utf-8")
    return path


def read_ids(path: Path) -> list[str]:
    return [tag.tag_id for tag in string_to_data(path.read_text(encoding="utf-8"), schema=PureDataSchema)]


def test_reserves_ids_in_later_files_before_allocation(tmp_path):
    first = write_source(tmp_path, "a.py", "# TODO: needs id <priority=high>\n")
    second = write_source(tmp_path, "b.py", "# TODO: already identified <id=1>\n")
    code, result = id_command.run([str(first), str(second)], counter_root=tmp_path)
    assert code == 0
    assert result.assigned == 1
    assert read_ids(first) == ["2"]
    assert read_ids(second) == ["1"]
    assert IdCounter.load(tmp_path).known_ids == {"1", "2"}


def test_existing_ids_are_saved_even_without_new_assignments(tmp_path):
    path = write_source(tmp_path, "a.py", "# TODO: existing <id=9>\n")
    before = path.read_bytes()
    id_command.run([str(path)], counter_root=tmp_path)
    assert IdCounter.load(tmp_path).next_id == 10
    assert path.read_bytes() == before


def test_parent_issue_does_not_prevent_local_id_assignment(tmp_path):
    path = write_source(tmp_path, "a.py", "# TODO: first <issue=100>\n# TODO: second <issue=100>\n")
    code, result = id_command.run([str(path)], counter_root=tmp_path)
    assert code == 0
    assert result.assigned == 2
    assert read_ids(path) == ["1", "2"]
    assert path.read_text(encoding="utf-8").count("issue=100") == 2


def test_tracker_backed_tags_still_reserve_their_local_ids(tmp_path):
    path = write_source(
        tmp_path,
        "a.py",
        "# TODO: first <priority=high>\n# TODO: linked <id=8 tracker=https://github.com/acme/repo/issues/101>\n",
    )
    code, result = id_command.run([str(path)], counter_root=tmp_path)
    assert code == 0
    assert result.skipped_have_id == 1
    assert read_ids(path) == ["9", "8"]


@pytest.mark.parametrize("mode", [{}, {"dry_run": True}, {"check": True}])
def test_duplicate_ids_fail_before_any_write(tmp_path, mode):
    first = write_source(tmp_path, "a.py", "# TODO: needs id <priority=high>\n# TODO: duplicate <id=4>\n")
    second = write_source(tmp_path, "b.py", "# TODO: duplicate <id=4>\n")
    before = [first.read_bytes(), second.read_bytes()]
    with pytest.raises(DataTagError, match="Duplicate local id"):
        id_command.run([str(first), str(second)], counter_root=tmp_path, **mode)
    assert [first.read_bytes(), second.read_bytes()] == before
    assert not (tmp_path / COUNTER_FILENAME).exists()


def test_overlapping_input_paths_do_not_duplicate_physical_tags(tmp_path):
    path = write_source(tmp_path, "a.py", "# TODO: one <priority=high>\n")
    code, result = id_command.run([str(path), str(tmp_path), str(path)], counter_root=tmp_path)
    assert code == 0
    assert result.scanned == result.assigned == 1
    assert read_ids(path) == ["1"]


@pytest.mark.parametrize("mode", [{"dry_run": True}, {"check": True}])
def test_read_only_modes_do_not_persist_observed_ids(tmp_path, mode):
    path = write_source(tmp_path, "a.py", "# TODO: existing <id=5>\n")
    before = path.read_bytes()
    id_command.run([str(path)], counter_root=tmp_path, **mode)
    assert path.read_bytes() == before
    assert not (tmp_path / COUNTER_FILENAME).exists()


def test_corrupt_counter_prevents_source_writes(tmp_path):
    path = write_source(tmp_path, "a.py", "# TODO: one <priority=high>\n")
    counter_path = write_source(tmp_path, COUNTER_FILENAME, "broken json")
    before = path.read_bytes()
    with pytest.raises(DataTagError, match="refusing to reset"):
        id_command.run([str(path)], counter_root=tmp_path)
    assert path.read_bytes() == before
    assert counter_path.read_text(encoding="utf-8") == "broken json"


def test_failed_source_write_cannot_reuse_allocated_ids(tmp_path, monkeypatch):
    path = write_source(tmp_path, "a.py", "# TODO: one <priority=high>\n")

    def fail_write(*args, **kwargs):
        raise OSError("simulated source write failure")

    monkeypatch.setattr(id_command.mutator, "apply_mutations", fail_write)
    with pytest.raises(OSError, match="simulated"):
        id_command.run([str(path)], counter_root=tmp_path)
    assert IdCounter.load(tmp_path).next_id == 2


def test_shared_tracker_occurrences_receive_distinct_local_ids(tmp_path):
    from pycodetags import inspect_file
    from pycodetags.id_command import run

    path = tmp_path / "shared.py"
    path.write_bytes(
        b"# TODO: same\n# tracker=https://github.com/a/b/issues/1\nx = 1\n# TODO: same\n# tracker=https://github.com/a/b/issues/1\n"
    )
    assert run([str(path)], schema="TDG", counter_root=tmp_path, writer=lambda text: None)[1].assigned == 2
    tags = inspect_file(path, schema="TDG")
    assert [tag.tag_id for tag in tags] == ["1", "2"]
    assert tags[0].data_fields["tracker"] == tags[1].data_fields["tracker"]


def test_counter_save_uses_unique_temporary_and_cleans_failed_write(tmp_path, monkeypatch):
    import pycodetags.identity_counter as counter_module
    from pycodetags.identity_counter import IdCounter

    counter = IdCounter.load(tmp_path)
    unrelated = tmp_path / ".pycodetags_ids.tmp"
    unrelated.write_bytes(b"unrelated")
    counter.allocate("hash")

    def fail_replace(source, destination):
        assert source != unrelated
        raise OSError("replace failed")

    monkeypatch.setattr(counter_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        counter.save()
    assert unrelated.read_bytes() == b"unrelated"
    assert list(tmp_path.glob(".pycodetags-ids-*.tmp")) == []
