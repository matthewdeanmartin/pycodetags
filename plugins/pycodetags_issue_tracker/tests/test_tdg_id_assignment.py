"""Built-in TDG identity and plugin conversion agree with the core contract."""

from dataclasses import replace

from pycodetags_issue_tracker.converters import convert_data_to_TODO

from pycodetags import inspect_file, update_tags
from pycodetags.id_command import run


def test_parent_issue_gets_local_id_and_converted_record_can_be_updated(tmp_path):
    path = tmp_path / "source.py"
    path.write_bytes(b"# TODO: title\n# issue=100 estimate=30m\n# body\n")
    code, result = run([str(path)], schema="TDG", counter_root=tmp_path, writer=lambda text: None)
    assert code == 0 and result.assigned == 1
    old = convert_data_to_TODO(inspect_file(path, schema="TDG")[0])
    assert (old.issue, old.tag_id, old.estimate) == ("100", "1", 0.5)
    update_tags(path, [(old, replace(old, title="new"))])
    parsed = inspect_file(path, schema="TDG")[0]
    assert (parsed.title, parsed.body, parsed.tag_id) == ("new", "body", "1")
    assert run([str(path)], schema="TDG", counter_root=tmp_path, writer=lambda text: None)[1].assigned == 0
