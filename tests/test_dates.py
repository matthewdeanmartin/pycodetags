import datetime

import pytest

from pycodetags.todo_tag_types import parse_due_date


def test_parse_due_date_valid():
    dt = parse_due_date("2024-12-31")
    assert dt == datetime.datetime(2024, 12, 31)


def test_parse_due_date_invalid():
    with pytest.raises(ValueError) as exc:
        parse_due_date("12/31/2024")
    assert "Invalid date format" in str(exc.value)
