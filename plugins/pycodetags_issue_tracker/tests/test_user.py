import subprocess

from pycodetags_issue_tracker.user import get_git_user, get_os_user


def test_get_git_user_success(monkeypatch):
    monkeypatch.setattr(subprocess, "check_output", lambda cmd: b"gituser\n")
    assert get_git_user() == "gituser"


def test_get_os_user_env(monkeypatch):
    monkeypatch.setenv("USER", "u1")
    assert get_os_user() == "u1"
    monkeypatch.delenv("USER")
    monkeypatch.setenv("USERNAME", "u2")
    assert get_os_user() == "u2"
    monkeypatch.delenv("USERNAME")
    assert get_os_user() == "unknown_os_user"
