import subprocess

import pytest

# Import functions to test
from pycodetags.user import get_current_user, get_env_user, get_git_user, get_os_user


@pytest.fixture(autouse=True)
def clear_git_cache():
    # clear the lru_cache on get_git_user before each test
    get_git_user.cache_clear()
    yield
    get_git_user.cache_clear()


def test_get_git_user_success(monkeypatch):
    expected = b"TestUser\n"

    def fake_check_output(cmd):
        assert cmd == ["git", "config", "user.name"]
        return expected

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    result = get_git_user()
    assert result == "TestUser"

    # test cache: monkey-patch to raise and still get cached value
    def raise_error(cmd):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

    monkeypatch.setattr(subprocess, "check_output", raise_error)
    # still returns cached
    assert get_git_user() == "TestUser"


def test_get_git_user_failure(monkeypatch):
    def raise_error(cmd):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

    monkeypatch.setattr(subprocess, "check_output", raise_error)
    result = get_git_user()
    assert result == "unknown_git_user"


def test_get_git_user_no_git(monkeypatch):
    monkeypatch.setattr(subprocess, "check_output", lambda cmd: (_ for _ in ()).throw(FileNotFoundError()))
    result = get_git_user()
    assert result == "unknown_git_user"


def test_get_os_user_prefers_user(monkeypatch):
    monkeypatch.setenv("USER", "alice")
    monkeypatch.delenv("USERNAME", raising=False)
    assert get_os_user() == "alice"


def test_get_os_user_fallback_username(monkeypatch):
    monkeypatch.setenv("USERNAME", "bob")
    monkeypatch.delenv("USER", raising=False)
    assert get_os_user() == "bob"


def test_get_os_user_unknown(monkeypatch):
    monkeypatch.delenv("USER", raising=False)
    monkeypatch.delenv("USERNAME", raising=False)
    assert get_os_user() == "unknown_os_user"


def test_get_env_user_set(monkeypatch):
    monkeypatch.setenv("MY_ENV_USER", "carol")
    assert get_env_user("MY_ENV_USER") == "carol"


def test_get_env_user_not_set(monkeypatch):
    monkeypatch.delenv("NO_SUCH_ENV", raising=False)
    assert get_env_user("NO_SUCH_ENV") == ""


def test_get_current_user_git(monkeypatch):
    # mock git
    monkeypatch.setattr("pycodetags.user.get_git_user", lambda: "gitguy")
    assert get_current_user("git", "IGNORED") == "gitguy"


def test_get_current_user_env(monkeypatch):
    monkeypatch.setenv("XYZ", "envgal")
    assert get_current_user("env", "XYZ") == "envgal"


def test_get_current_user_os(monkeypatch):
    monkeypatch.setenv("USER", "osdude")
    monkeypatch.delenv("USERNAME", raising=False)
    assert get_current_user("os", "IGNORED") == "osdude"


def test_get_current_user_unknown_method():
    with pytest.raises(NotImplementedError) as exc:
        get_current_user("foo", "VAR")
    assert "Not a known ID method" in str(exc.value)
