import datetime
import json

from pycodetags_issue_tracker.todo_tag_types import TODO

from pycodetags.views import print_changelog, print_json


def test_print_json(capsys):
    class Dummy:
        def to_dict(self):
            return {}

    dummy = Dummy()
    dummy.todo_meta = type("X", (), {"to_dict": lambda self: {"a": 1}})()
    d2 = Dummy()
    d2.todo_meta = TODO(status="done", tracker="u", release="v2", closed_date=None)
    d2.todo_meta.closed_date = None
    found = {"dones": [d2], "todos": [dummy]}
    print_json(found)
    out = capsys.readouterr().out
    obj = json.loads(out)
    assert "todos" in obj


def test_print_changelog_order(capsys, monkeypatch):
    d1 = TODO(status="done", tracker="http://x/1", change_type="Added", comment="Desc1", release="1.0")
    d1.todo_meta = d1
    d2 = TODO(status="done", tracker="http://x/2", change_type="Fixed", comment="Desc2", release="1.0")
    d2.todo_meta = d2
    d3 = TODO(status="done", tracker="http://x/3", change_type="Changed", comment="Desc3", release="2.0")
    d3.todo_meta = d3
    for d in (d1, d2, d3):
        # assign meta and closed_date
        def dummy_func():
            pass

        wrapped = d(dummy_func)
        # assign date so 3 first
        d.closed_date = datetime.datetime(2025, 1, 1)
        wrapped.todo_meta = d
    found = {"todos": [d1, d2, d3]}
    print_changelog(found)
    out = capsys.readouterr().out
    # Check versions in headers
    assert "## [2.0]" in out and "## [1.0]" in out
    assert "- Desc3" in out and "- Desc1" in out
