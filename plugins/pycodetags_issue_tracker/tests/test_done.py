from pycodetags_issue_tracker.todo_tag_types import TODO


def sample_fn(x):
    return x * 2


def test_done_decorator_and_repr(monkeypatch):
    done = TODO(status="done", tracker="http://issue/123", change_type="Fixed", comment=None, release="v1")
    wrapped = done(sample_fn)
    result = wrapped(5)
    assert result == 10
    assert hasattr(wrapped, "todo_meta") and wrapped.todo_meta is done

    rep = repr(done)
    assert "change_type='Fixed'" in rep or 'change_type="Fixed"' in rep
