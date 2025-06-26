# import pytest
# import warnings
# import datetime
# import os
# from code_tags.main_types import TODO, NotImplementedException, parse_due_date
# from code_tags.config import settings
#
# @pytest.fixture(scope="session", autouse=True)
# def set_test_settings():
#     settings.configure(FORCE_ENV_FOR_DYNACONF="testing")
#
# def test_todo_basic_decorator(monkeypatch):
#     monkeypatch.setattr("code_tags.main_types.get_current_user", lambda: "alice")
#     # monkeypatch.setattr("code_tags.main_types.settings", make_settings({"ACTION_ON_PAST_DUE": False, "ACTION_ON_USER_MATCH": False}))
#     td = TODO(assignee="alice", message="Test", due_date=None)
#     @td
#     def f():
#         return "ok"
#     assert f() == "ok"
#
# def test_todo_warn_on_user(monkeypatch):
#     monkeypatch.setattr("code_tags.main_types.get_current_user", lambda: "bob")
#     # monkeypatch.setattr("code_tags.main_types.settings", make_settings({
#     #     "ACTION_ON_PAST_DUE": False,
#     #     "ACTION_ON_USER_MATCH": True,
#     #     "ACTION": "warn"
#     # }))
#     td = TODO(assignee="bob", due_date=None)
#     @td
#     def f(): return True
#     with warnings.catch_warnings(record=True) as w:
#         warnings.simplefilter("always")
#         assert f()
#         assert any("TODO Reminder" in str(wi.message) for wi in w)
#
# def test_todo_stop_on_past_due(monkeypatch):
#     monkeypatch.setattr("code_tags.main_types.get_current_user", lambda: "someone")
#     # monkeypatch.setattr("code_tags.main_types.settings", make_settings({
#     #     "ACTION_ON_PAST_DUE": True,
#     #     "ACTION_ON_USER_MATCH": False,
#     #     "ACTION": "stop"
#     # }))
#     due = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%m/%d/%Y")
#     td = TODO(assignee="other", due_date=due, message="Late")
#     @td
#     def f(): pass
#     with pytest.raises(NotImplementedException) as exc:
#         f()
#     assert "TODO Reminder" in str(exc.value)
from pycodetags import TODO


def test_to_str():
    x = TODO(
        assignee="Alice",
        iteration="3",
        status="Planning",
        release_due="2.0.0",
        tracker="https://example.com/FSH-16",
        comment="Add proper game over screen and restart option for enhanced gameplay loop.",
    )
    result = x.as_pep350_comment()
    assert "Alice" in result
