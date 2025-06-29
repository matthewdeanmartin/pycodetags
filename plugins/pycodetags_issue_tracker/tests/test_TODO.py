from pycodetags_issue_tracker.todo_tag_types import TODO


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
