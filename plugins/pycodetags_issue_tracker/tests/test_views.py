import datetime

from pycodetags_issue_tracker.schema.todo_tag_types import TODO
from pycodetags_issue_tracker.views.views import print_changelog


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
    found = [d1, d2, d3]
    print_changelog(found)
    out = capsys.readouterr().out
    # Check versions in headers
    assert "## [2.0]" in out and "## [1.0]" in out
    assert "- Desc3" in out and "- Desc1" in out
