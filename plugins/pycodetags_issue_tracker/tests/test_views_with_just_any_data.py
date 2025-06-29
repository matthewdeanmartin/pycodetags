import datetime

import pycodetags_issue_tracker.views as views
import pytest
from pycodetags_issue_tracker import TODO


@pytest.fixture(scope="session", autouse=True)
def sample_data() -> list[TODO]:
    td = TODO(tracker="http://x/1", change_type="Added", comment="Desc1")
    td.todo_meta = td

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

    d3 = TODO(status="todo", tracker="http://x/3", change_type="Changed", comment="Desc3", release="2.0")
    d3.todo_meta = d3

    found = [td, d1, d2, d3]
    return found


def test_html(sample_data):
    views.print_html(sample_data)


def test_text(sample_data):
    views.print_text(sample_data)


def test_print_changelog(sample_data):
    views.print_changelog(sample_data)


def test_print_todo_md(sample_data):
    views.print_todo_md(sample_data)


def test_print_validate(sample_data):
    views.print_validate(sample_data)


def test_print_done_file(sample_data):
    views.print_done_file(sample_data)
