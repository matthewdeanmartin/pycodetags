# import datetime
# import warnings
#
# import pytest
# from pycodetags_issue_tracker.todo_tag_types import TODO, DueException, get_code_tags_config, parse_due_date
#
# from pycodetags.config import CodeTagsConfig
#
#
# class DummyConfig(CodeTagsConfig):
#     def __init__(self, pyproject_path: str = "pyproject.toml"):
#         super().__init__(pyproject_path, "me")
#         self.config = {
#             "disable_all_runtime_behavior": False,
#             "enable_actions": True,
#             "disable_on_ci": False,
#             "action_on_past_due": True,
#             "action_only_on_responsible_user": False,
#             "default_action": "warn",
#             "closed_status": ["done", "closed"],
#             "valid_status": ["todo", "done"],
#             "valid_priorities": ["high"],
#             "valid_iterations": ["1", "2", "3", "4"],
#             "valid_categories": ["cat1", "cat2"],
#             "mandatory_fields": ["assignee", "originator", "origination_date"],
#             "valid_authors": ["alice"],
#             "valid_releases": ["1.0.0"],
#             "valid_custom_field_names": ["cf1"],
#         }
#
#     @classmethod
#     def get_instance(cls, pyproject_path="pyproject.toml"):
#         return cls()
#
#
# @pytest.fixture(autouse=True)
# def use_fixed_config(tmp_path, monkeypatch):
#     CodeTagsConfig.set_instance(DummyConfig())
#     yield
#     CodeTagsConfig.set_instance(None)
#
#
# def test_parse_due_date_valid():
#     dt = parse_due_date("2025-12-31")
#     assert isinstance(dt, datetime.datetime)
#     assert dt.date() == datetime.date(2025, 12, 31)
#
#
# def test_parse_due_date_invalid():
#     with pytest.raises(ValueError):
#         parse_due_date("2025-13-01")
#
#
# def test_is_probably_done_by_closed_date_and_status(tmp_path):
#     t = TODO(assignee="alice", originator="alice", comment="c")
#     assert not t.is_probably_done()
#     t.closed_date = datetime.datetime.now()
#     assert t.is_probably_done()
#     t2 = TODO(assignee="bob", originator="bob", status="DONE", comment="c")
#     assert t2.is_probably_done()
#
#
# def test_current_user_and_set_current_user_func():
#
#     t = TODO(assignee="me", originator="me", comment="c")
#     assert t.current_user == "me"
#
#
# def test_perform_action_warn(monkeypatch):
#
#     due = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
#     t = TODO(assignee="me", originator="alice", comment="c", due=due)
#
#     # wrap a dummy function to attach decorator
#     @t
#     def f():
#         return 1
#
#     with warnings.catch_warnings(record=True) as rec:
#         f()
#         list(rec)
#         assert any("TODO Reminder" in str(w.message) for w in rec)
#
#
# def test_perform_action_stop(monkeypatch):
#     # change config default_action to stop
#     cfg = get_code_tags_config()
#     # pylint: disable=protected-access
#     cfg.config["default_action"] = "stop"
#     cfg.user_override = "me"
#     due = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
#     t = TODO(assignee="me", originator="alice", comment="c", due=due)
#
#     @t
#     def dummy():
#         return None
#
#     with pytest.raises(DueException) as ei:
#         dummy()
#     assert "TODO Reminder" in str(ei.value)
#
#
# def test_validate_missing_fields_and_invalids():
#     t = TODO(
#         assignee=None,
#         originator="bob",
#         comment="x",
#         status="done",
#         release=None,
#         closed_date=None,
#         priority="low",
#         custom_fields={"bad": "v"},
#         iteration="it",
#         category="cat",
#     )
#     issues = t.validate()
#     assert "missing assignee" in " ".join(issues).lower()
#     assert "missing release" in " ".join(issues).lower()
#     assert "missing closed date" in " ".join(issues).lower()
#     assert "invalid priority" in " ".join(issues).lower()
#     assert "invalid iteration" in " ".join(issues).lower()
#     assert "invalid category" in " ".join(issues).lower()
#     assert "custom field 'bad'" in " ".join(issues).lower()
#     assert "person 'bob' is not on the valid authors" in " ".join(issues).lower()
#
#
# def test_as_pep350_comment_truncates_and_includes_fields():
#     t = TODO(
#         # default fields
#         assignee="a",
#         # data fields
#         code_tag="BUG",
#         comment="something happened",
#         originator="b",
#         due="2025-01-01",
#         priority="high",
#         status=None,
#         custom_fields={"cf1": "v"},
#     )
#     txt = t.as_pep350_comment()
#     assert txt.startswith("# BUG:")
#     assert "<a " in txt
#     assert "originator:b" in txt
#     assert "due:2025-01-01" in txt
#     assert "priority:high" in txt
#     assert "cf1:v" in txt
#
#
# def test_decorator_attaches_meta_and_preserves_signature():
#     t = TODO(assignee="u", originator="u", comment="x")
#
#     @t
#     def add(a, b):
#         return a + b
#
#     assert hasattr(add, "todo_meta")
#     assert add(2, 3) == 5
